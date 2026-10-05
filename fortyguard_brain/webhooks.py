from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

import requests


class _Response(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


PostCallable = Callable[..., _Response]


class WebhookError(RuntimeError):
    """Raised when an n8n webhook cannot provide a usable response."""


def _post_json(
    url: str,
    payload: dict[str, str],
    *,
    timeout: float,
    post: PostCallable,
) -> Any:
    try:
        response = post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise WebhookError("The webhook request failed.") from exc


def send_chat_message(
    url: str,
    message: str,
    email: str,
    *,
    timeout: float = 90.0,
    post: PostCallable | None = None,
) -> str:
    """Send one chat turn to n8n and return its Markdown response."""
    post = post or requests.post
    data = _post_json(
        url,
        {"chatInput": message, "sessionId": email},
        timeout=timeout,
        post=post,
    )

    if not isinstance(data, dict):
        raise WebhookError("The chat webhook returned an unexpected response.")

    output = data.get("output")
    if not isinstance(output, str) or not output.strip():
        raise WebhookError("The chat webhook returned no output.")

    return output


def reset_chat_memory(
    url: str,
    email: str,
    *,
    timeout: float = 90.0,
    post: PostCallable | None = None,
) -> bool:
    """Ask n8n to reset the user's memory and report explicit confirmation."""
    post = post or requests.post
    data = _post_json(
        url,
        {"email": email},
        timeout=timeout,
        post=post,
    )
    return isinstance(data, dict) and data.get("status") == "done"
