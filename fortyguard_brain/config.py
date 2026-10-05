from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Protocol


class SecretsStore(Protocol):
    """Subset of Streamlit's secrets API used by the app."""

    def load_if_toml_exists(self) -> bool: ...

    def merge_programmatic_secrets(
        self, programmatic_secrets: Mapping[str, Any]
    ) -> None: ...


AUTH_ENVIRONMENT_KEYS = {
    "FORTYGUARD_AUTH_REDIRECT_URI": "redirect_uri",
    "FORTYGUARD_AUTH_COOKIE_SECRET": "cookie_secret",
    "FORTYGUARD_AUTH_CLIENT_ID": "client_id",
    "FORTYGUARD_AUTH_CLIENT_SECRET": "client_secret",
    "FORTYGUARD_AUTH_SERVER_METADATA_URL": "server_metadata_url",
}

AUTH_CLIENT_KWARGS_ENVIRONMENT_KEYS = {
    "FORTYGUARD_AUTH_HOSTED_DOMAIN": "hd",
    "FORTYGUARD_AUTH_PROMPT": "prompt",
}

APP_ENVIRONMENT_KEYS = {
    "FORTYGUARD_ALLOWED_DOMAIN": "allowed_domain",
}

WEBHOOK_ENVIRONMENT_KEYS = {
    "FORTYGUARD_CHAT_WEBHOOK_URL": "chat_url",
    "FORTYGUARD_RESET_WEBHOOK_URL": "reset_url",
    "FORTYGUARD_REQUEST_TIMEOUT_SECONDS": "timeout_seconds",
}


def _mapped_values(
    environ: Mapping[str, str], variable_names: Mapping[str, str]
) -> dict[str, str]:
    values: dict[str, str] = {}
    for environment_name, setting_name in variable_names.items():
        value = environ.get(environment_name, "").strip()
        if value:
            values[setting_name] = value
    return values


def build_environment_secrets(environ: Mapping[str, str]) -> dict[str, Any]:
    """Build Streamlit-compatible secrets from deployment environment variables."""
    secrets: dict[str, Any] = {}

    auth = _mapped_values(environ, AUTH_ENVIRONMENT_KEYS)
    client_kwargs = _mapped_values(
        environ, AUTH_CLIENT_KWARGS_ENVIRONMENT_KEYS
    )
    if client_kwargs:
        auth["client_kwargs"] = client_kwargs
    if auth:
        secrets["auth"] = auth

    app = _mapped_values(environ, APP_ENVIRONMENT_KEYS)
    if app:
        secrets["app"] = app

    webhooks = _mapped_values(environ, WEBHOOK_ENVIRONMENT_KEYS)
    if webhooks:
        secrets["webhooks"] = webhooks

    return secrets


def configured_secrets_path_exists(paths: Iterable[str]) -> bool:
    """Return whether Streamlit has a non-empty file or directory secret source."""
    for configured_path in paths:
        path = Path(configured_path).expanduser()
        if path.is_file():
            return True
        if path.is_dir() and any(
            candidate.is_file() for candidate in path.rglob("*")
        ):
            return True
    return False


def build_programmatic_secrets(
    paths: Iterable[str], environ: Mapping[str, str]
) -> dict[str, Any] | None:
    """Return environment secrets only when no configured secret source exists."""
    if configured_secrets_path_exists(paths):
        return None
    return build_environment_secrets(environ) or None


def configure_streamlit_secrets(
    secrets_store: SecretsStore,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Load environment values only when no Streamlit secrets file exists.

    Returns ``True`` when environment-backed values were installed.
    """
    if secrets_store.load_if_toml_exists():
        return False

    environment_secrets = build_environment_secrets(
        os.environ if environ is None else environ
    )
    if not environment_secrets:
        return False

    secrets_store.merge_programmatic_secrets(environment_secrets)
    return True
