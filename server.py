from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st
from streamlit import config as streamlit_config

from fortyguard_brain.config import (
    build_programmatic_secrets,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def _environment_secrets() -> dict[str, Any] | None:
    configured_paths = [
        *streamlit_config.get_option("secrets.files"),
        str(PROJECT_ROOT / ".streamlit" / "secrets.toml"),
    ]
    return build_programmatic_secrets(configured_paths, os.environ)


app = st.App(PROJECT_ROOT / "app.py", secrets=_environment_secrets())


if __name__ == "__main__":
    server_config: dict[str, Any] = {
        "server.address": "0.0.0.0",
        "server.headless": True,
    }
    platform_port = os.environ.get("PORT", "").strip()
    if platform_port:
        try:
            server_config["server.port"] = int(platform_port)
        except ValueError as exc:
            raise RuntimeError("PORT must be a valid integer.") from exc

    app.run(config=server_config)
