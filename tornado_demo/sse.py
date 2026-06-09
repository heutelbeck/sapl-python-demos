"""Render an enforced item stream as server-sent events on a Tornado handler.

`sse_write` consumes an enforced async iterator: permitted items become `data:`
frames, `AccessGrantedSignal` / `AccessSuspendedSignal` become boundary frames, and
`AccessDeniedError` becomes a final `ACCESS_DENIED` frame.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import tornado.web

from sapl_base.pep import AccessDeniedError, AccessGrantedSignal, AccessSuspendedSignal


def _format_sse(data: Any) -> str:
    if isinstance(data, AccessSuspendedSignal):
        return "data: " + json.dumps({"type": "ACCESS_SUSPENDED"}) + "\n\n"
    if isinstance(data, AccessGrantedSignal):
        return "data: " + json.dumps({"type": "ACCESS_GRANTED"}) + "\n\n"
    if isinstance(data, dict):
        return f"data: {json.dumps(data)}\n\n"
    return f"data: {data}\n\n"


async def sse_write(handler: tornado.web.RequestHandler, enforced: AsyncIterator[Any]) -> None:
    """Write an enforced item stream to a Tornado handler as server-sent events."""
    handler.set_header("Content-Type", "text/event-stream")
    handler.set_header("Cache-Control", "no-cache")
    try:
        async for item in enforced:
            handler.write(_format_sse(item))
            await handler.flush()
    except AccessDeniedError as exc:
        handler.write(_format_sse({"type": "ACCESS_DENIED", "reason": getattr(exc, "reason", None)}))
        await handler.flush()
    if not handler._finished:
        handler.finish()
