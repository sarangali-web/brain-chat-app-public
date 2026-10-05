# FortyGuard Brain

A lightweight internal Streamlit chat interface for the existing FortyGuard Brain
workflows in n8n. The app contains no database, retrieval, memory, or RAG logic.
Google OIDC provides the authenticated, verified email that is sent to n8n as the
persistent session identifier.

## What it does

- Allows only authenticated Google Workspace identities with a verified
  `@fortyguard.com` email address and matching signed hosted-domain claim.
- Sends chat turns to the Brain webhook as `chatInput` and `sessionId`.
- Renders n8n's `output` as Markdown, including clickable Jira and Google links.
- Keeps visible messages only in the current Streamlit session.
- Resets server-side memory through n8n and clears local messages only after n8n
  returns `{"status": "done"}`.

## Local setup

1. Create a Google OAuth **Web application** client. Add this authorized redirect
   URI:

   ```text
   http://localhost:8501/oauth2callback
   ```

2. Copy the example Secrets file and fill in the OAuth values:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Generate a strong cookie secret, for example with
   `openssl rand -base64 32`. Never commit `.streamlit/secrets.toml`.

3. Install and run:

   ```bash
   python -m pip install -r requirements.txt
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud

1. Deploy this repository with `app.py` as the entrypoint.
2. Choose the final `*.streamlit.app` subdomain before configuring production
   authentication.
3. In the Google OAuth client, add the exact production redirect URI:

   ```text
   https://YOUR-APP.streamlit.app/oauth2callback
   ```

4. In the app's **Settings > Secrets**, paste the contents of
   `.streamlit/secrets.toml.example`, replace all OAuth placeholders, and set
   `auth.redirect_uri` to the same production callback URL.
5. If the Google Cloud project belongs to the FortyGuard Workspace organization,
   set the OAuth audience to **Internal**. The app still independently checks both
   `email_verified`, the exact `fortyguard.com` email domain, and Google's signed
   `hd` (hosted-domain) claim.

The webhook URLs, allowed domain, and timeout are configurable in Secrets. Their
checked-in defaults point to the requested FortyGuard n8n workflows.

## Deploy on another platform

When no Streamlit `secrets.toml` file is present, the app reads its configuration
from environment variables. Copy the names from `.env.example` into your hosting
platform's environment or secret manager:

```text
FORTYGUARD_AUTH_REDIRECT_URI
FORTYGUARD_AUTH_COOKIE_SECRET
FORTYGUARD_AUTH_CLIENT_ID
FORTYGUARD_AUTH_CLIENT_SECRET
FORTYGUARD_AUTH_SERVER_METADATA_URL
FORTYGUARD_AUTH_HOSTED_DOMAIN
FORTYGUARD_AUTH_PROMPT
FORTYGUARD_ALLOWED_DOMAIN
FORTYGUARD_CHAT_WEBHOOK_URL
FORTYGUARD_RESET_WEBHOOK_URL
FORTYGUARD_REQUEST_TIMEOUT_SECONDS
```

The first five variables are required for Google sign-in. Use the deployment's
public callback URL for `FORTYGUARD_AUTH_REDIRECT_URI`, ending exactly in
`/oauth2callback`, and register the same URL in the matching Google OAuth client.
The remaining variables are optional because the checked-in defaults preserve the
current FortyGuard domain, Google sign-in behavior, n8n endpoints, and timeout.

The application reads real process environment variables; it does not load a local
`.env` file automatically. For local development, either export the variables in
your shell or continue using `.streamlit/secrets.toml`. If both configuration
methods are available, `secrets.toml` takes precedence and environment values are
ignored.

On a generic Python host, use the included launcher as the start command:

```bash
python server.py
```

The launcher uses Streamlit's ASGI application API so the environment-backed
authentication settings are installed before OAuth routes begin handling requests.
It binds to `0.0.0.0`, uses the platform's `PORT` variable when present, and falls
back to port 8501 otherwise. Continue using `app.py` as the Streamlit Community
Cloud entrypoint.

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest
```

The tests verify strict domain handling, configuration-source precedence,
environment-variable mapping, the exact webhook payloads, Markdown output
handling, and reset confirmation behavior without contacting n8n.
