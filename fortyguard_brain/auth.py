from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def get_verified_org_email(
    claims: Mapping[str, Any], allowed_domain: str = "fortyguard.com"
) -> str | None:
    """Return a normalized email for an authenticated Google Workspace user."""
    if (
        claims.get("is_logged_in") is not True
        or claims.get("email_verified") is not True
    ):
        return None

    email = str(claims.get("email", "")).strip().lower()
    domain = allowed_domain.strip().lower().lstrip("@")

    if not email or not domain or email.count("@") != 1:
        return None

    local_part, email_domain = email.rsplit("@", 1)
    hosted_domain = str(claims.get("hd", "")).strip().lower()
    if not local_part or email_domain != domain or hosted_domain != domain:
        return None

    return email
