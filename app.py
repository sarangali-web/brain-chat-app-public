from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st
from streamlit.errors import (
    StreamlitAuthError,
    StreamlitMissingAuthlibError,
    StreamlitSecretNotFoundError,
)

from fortyguard_brain.auth import get_verified_org_email
from fortyguard_brain.config import configure_streamlit_secrets
from fortyguard_brain.webhooks import WebhookError, reset_chat_memory, send_chat_message


APP_TITLE = "FortyGuard Brain"
APP_SUBTITLE = "Internal Knowledge Assistant"
DEFAULT_ALLOWED_DOMAIN = "fortyguard.com"
DEFAULT_CHAT_WEBHOOK_URL = (
    "https://n8n-kczt.srv1629125.hstgr.cloud/webhook/brain-message"
)
DEFAULT_RESET_WEBHOOK_URL = (
    "https://n8n-kczt.srv1629125.hstgr.cloud/webhook/reset-chat"
)
DEFAULT_REQUEST_TIMEOUT_SECONDS = 90.0


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="auto",
)

# Streamlit Community Cloud supplies a secrets file. Other deployment platforms
# can provide the same settings through FORTYGUARD_* environment variables.
configure_streamlit_secrets(st.secrets)


def _secret_section(name: str) -> Mapping[str, Any]:
    """Read a Secrets section without making the local setup screen crash."""
    try:
        value = st.secrets.get(name, {})
    except StreamlitSecretNotFoundError:
        return {}
    return value if isinstance(value, Mapping) else {}


def _setting(section: str, key: str, default: str) -> str:
    value = _secret_section(section).get(key, default)
    return str(value).strip() or default


def _timeout_setting() -> float:
    raw_timeout = _setting(
        "webhooks", "timeout_seconds", str(DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )
    try:
        timeout = float(raw_timeout)
    except ValueError:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS
    return timeout if timeout > 0 else DEFAULT_REQUEST_TIMEOUT_SECONDS


def _auth_is_configured() -> bool:
    auth = _secret_section("auth")
    required = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )
    return all(str(auth.get(key, "")).strip() for key in required)


ALLOWED_DOMAIN = _setting("app", "allowed_domain", DEFAULT_ALLOWED_DOMAIN).lower()
CHAT_WEBHOOK_URL = _setting(
    "webhooks", "chat_url", DEFAULT_CHAT_WEBHOOK_URL
)
RESET_WEBHOOK_URL = _setting(
    "webhooks", "reset_url", DEFAULT_RESET_WEBHOOK_URL
)
REQUEST_TIMEOUT_SECONDS = _timeout_setting()


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --fg-ink: #002e46;
                --fg-muted: #61717a;
                --fg-blue: #1769b0;
                --fg-blue-bright: #0095e0;
                --fg-pale: #e6f0f5;
                --fg-line: #d9e6ec;
                --fg-warm: #ffffff;
            }

            .stApp {
                background:
                    radial-gradient(circle at 50% -8%, rgba(0, 149, 224, 0.09), transparent 31rem),
                    var(--fg-warm);
            }

            [data-testid="stHeader"] {
                background: rgba(255, 255, 255, 0.88);
                backdrop-filter: blur(10px);
            }

            .block-container {
                max-width: 850px;
                padding-top: 2.2rem;
                padding-bottom: 7.5rem;
            }

            .brain-header {
                display: flex;
                align-items: center;
                gap: 0.95rem;
                margin-bottom: 1.8rem;
            }

            .brain-mark {
                align-items: center;
                background: linear-gradient(145deg, var(--fg-blue-bright), var(--fg-blue));
                border-radius: 15px;
                box-shadow: 0 8px 24px rgba(23, 105, 176, 0.20);
                color: white;
                display: flex;
                flex: 0 0 48px;
                font-size: 1rem;
                font-weight: 750;
                height: 48px;
                justify-content: center;
                letter-spacing: -0.04em;
                width: 48px;
            }

            .brain-header h1 {
                color: var(--fg-ink);
                font-size: clamp(1.65rem, 4vw, 2rem);
                font-weight: 720;
                letter-spacing: -0.035em;
                line-height: 1.08;
                margin: 0;
            }

            .brain-header p {
                color: var(--fg-muted);
                font-size: 0.92rem;
                margin: 0.28rem 0 0;
            }

            .empty-state {
                border: 1px solid var(--fg-line);
                border-radius: 18px;
                color: var(--fg-muted);
                margin: 4.5rem auto 1.5rem;
                max-width: 510px;
                padding: 1.4rem 1.6rem;
                text-align: center;
                background: rgba(255, 255, 255, 0.64);
                box-shadow: 0 8px 30px rgba(0, 46, 70, 0.04);
            }

            .empty-state strong {
                color: var(--fg-ink);
                display: block;
                font-size: 1.02rem;
                font-weight: 650;
                margin-bottom: 0.35rem;
            }

            .login-shell {
                margin: 11vh auto 0;
                max-width: 480px;
                text-align: center;
            }

            .login-shell .brain-mark {
                height: 58px;
                margin: 0 auto 1.25rem;
                width: 58px;
            }

            .login-shell h1 {
                color: var(--fg-ink);
                font-size: 2rem;
                letter-spacing: -0.04em;
                margin-bottom: 0.35rem;
            }

            .login-shell p {
                color: var(--fg-muted);
                margin: 0 auto 1.6rem;
            }

            [data-testid="stChatMessage"] {
                background: rgba(255, 255, 255, 0.76);
                border: 1px solid var(--fg-line);
                border-radius: 18px;
                box-shadow: 0 6px 22px rgba(0, 46, 70, 0.035);
                margin-bottom: 0.75rem;
                padding: 0.9rem 1rem;
            }

            [data-testid="stChatMessage"] a {
                color: var(--fg-blue);
                font-weight: 600;
                text-decoration-color: rgba(23, 105, 176, 0.35);
                text-underline-offset: 0.16em;
            }

            [data-testid="stChatMessage"] a:hover {
                text-decoration-color: var(--fg-blue);
            }

            [data-testid="stChatInput"] {
                background: white;
                border: 1px solid #d5e2dd;
                border-radius: 17px;
                box-shadow: 0 12px 36px rgba(0, 46, 70, 0.12);
            }

            [data-testid="stChatInput"]:focus-within {
                border-color: var(--fg-blue);
                box-shadow: 0 12px 36px rgba(23, 105, 176, 0.15);
            }

            [data-testid="stSidebar"] {
                background: var(--fg-pale);
                border-right: 1px solid var(--fg-line);
            }

            [data-testid="stSidebar"] h2 {
                color: var(--fg-ink);
                font-size: 1.08rem;
                letter-spacing: -0.02em;
            }

            .sidebar-brand {
                color: var(--fg-ink);
                font-size: 0.82rem;
                font-weight: 750;
                letter-spacing: 0.08em;
                margin: 0.4rem 0 1.8rem;
                text-transform: uppercase;
            }

            .stButton > button[kind="primary"] {
                background: var(--fg-blue);
                border-color: var(--fg-blue);
            }

            .stButton > button[kind="primary"]:hover {
                background: var(--fg-ink);
                border-color: var(--fg-ink);
            }

            @media (max-width: 640px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                    padding-top: 1.25rem;
                }

                .brain-header {
                    margin-bottom: 1.25rem;
                }

                .brain-mark {
                    border-radius: 13px;
                    flex-basis: 43px;
                    height: 43px;
                    width: 43px;
                }

                .empty-state {
                    margin-top: 2.5rem;
                }

                [data-testid="stChatMessage"] {
                    border-radius: 15px;
                    padding: 0.75rem 0.8rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        f"""
        <div class="brain-header">
            <div class="brain-mark" aria-hidden="true">FG</div>
            <div>
                <h1>{APP_TITLE}</h1>
                <p>{APP_SUBTITLE}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_login() -> None:
    st.markdown(
        f"""
        <div class="login-shell">
            <div class="brain-mark" aria-hidden="true">FG</div>
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}<br>Sign in with your FortyGuard Google account.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 1.8, 1])
    with center:
        st.button(
            "Continue with Google",
            on_click=st.login,
            type="primary",
            use_container_width=True,
        )
        st.caption("Access is limited to verified @fortyguard.com accounts.")


def _render_auth_setup() -> None:
    _render_header()
    st.error("Google sign-in has not been configured for this deployment yet.")
    st.info(
        "Add the `[auth]` values from `.streamlit/secrets.toml.example` to "
        "Streamlit Secrets, or set the required `FORTYGUARD_AUTH_*` "
        "environment variables, then restart the app."
    )


def _sign_out() -> None:
    st.session_state.clear()
    st.logout()


def _render_access_denied(email: str | None) -> None:
    _render_header()
    st.error("This app is only available to verified @fortyguard.com accounts.")
    if email:
        st.caption(f"Signed in as: {email}")
    st.button("Sign Out", on_click=_sign_out, type="primary")


def _initialize_history(email: str) -> None:
    if st.session_state.get("history_owner") != email:
        st.session_state["messages"] = []
        st.session_state["history_owner"] = email
    elif "messages" not in st.session_state:
        st.session_state["messages"] = []


def _reset_session(email: str) -> None:
    with st.spinner("Resetting session..."):
        try:
            reset_done = reset_chat_memory(
                RESET_WEBHOOK_URL,
                email,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except WebhookError:
            st.error("We couldn't reset the chat right now. Your chat history is unchanged.")
            return

    if not reset_done:
        st.error("The reset was not confirmed. Your chat history is unchanged.")
        return

    st.session_state["messages"] = []
    st.success("Chat session reset successfully.")


def _render_sidebar(email: str) -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">FortyGuard Brain</div>', unsafe_allow_html=True)
        st.subheader("Session")
        if st.button("Reset Session", use_container_width=True):
            _reset_session(email)

        st.caption(f"Signed in as: {email}")
        st.button("Sign Out", on_click=_sign_out, use_container_width=True)


def _render_message(message: Mapping[str, str]) -> None:
    role = message.get("role", "assistant")
    avatar = "🧠" if role == "assistant" else None
    with st.chat_message(role, avatar=avatar):
        st.markdown(message.get("content", ""))


def _run_chat(email: str) -> None:
    _render_header()

    messages: list[dict[str, str]] = st.session_state["messages"]
    if not messages:
        st.markdown(
            """
            <div class="empty-state">
                <strong>What can I help you find?</strong>
                Ask about FortyGuard knowledge, projects, documents, or internal processes.
            </div>
            """,
            unsafe_allow_html=True,
        )

    for message in messages:
        _render_message(message)

    prompt = st.chat_input("Ask FortyGuard Brain...")
    if not prompt:
        return

    prompt = prompt.strip()
    if not prompt:
        return

    user_message = {"role": "user", "content": prompt}
    messages.append(user_message)
    _render_message(user_message)

    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("Searching FortyGuard Brain..."):
            try:
                answer = send_chat_message(
                    CHAT_WEBHOOK_URL,
                    prompt,
                    email,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            except WebhookError:
                st.error(
                    "FortyGuard Brain couldn't complete that request. "
                    "Please try again in a moment."
                )
                return

        assistant_message = {"role": "assistant", "content": answer}
        messages.append(assistant_message)
        st.markdown(answer)


def main() -> None:
    _apply_styles()

    if not _auth_is_configured():
        _render_auth_setup()
        st.stop()

    try:
        user_claims = st.user.to_dict()
    except (StreamlitAuthError, StreamlitMissingAuthlibError):
        _render_auth_setup()
        st.stop()

    if user_claims.get("is_logged_in") is not True:
        _render_login()
        st.stop()

    email = get_verified_org_email(user_claims, ALLOWED_DOMAIN)
    if email is None:
        claimed_email = str(user_claims.get("email", "")).strip().lower() or None
        _render_access_denied(claimed_email)
        st.stop()

    _initialize_history(email)
    _render_sidebar(email)
    _run_chat(email)


if __name__ == "__main__":
    main()
