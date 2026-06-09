"""Render an enforced item stream as server-sent events.

`sse_response` consumes an enforced async iterator: permitted items become `data:`
frames, `AccessGrantedSignal` / `AccessSuspendedSignal` become boundary frames, and
`AccessDeniedError` becomes a final `ACCESS_DENIED` frame. `sse_rendered` adapts a
handler that returns such an iterator into one that responds with SSE.
"""

from __future__ import annotations

import functools
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from django.http import StreamingHttpResponse

from sapl_base.pep import AccessDeniedError, AccessGrantedSignal, AccessSuspendedSignal


def _format_sse(data: Any) -> str:
    if isinstance(data, AccessSuspendedSignal):
        return "data: " + json.dumps({"type": "ACCESS_SUSPENDED"}) + "\n\n"
    if isinstance(data, AccessGrantedSignal):
        return "data: " + json.dumps({"type": "ACCESS_GRANTED"}) + "\n\n"
    if isinstance(data, dict):
        return f"data: {json.dumps(data)}\n\n"
    return f"data: {data}\n\n"


def sse_response(enforced: AsyncIterator[Any]) -> StreamingHttpResponse:
    """Render an enforced item stream as server-sent events."""

    async def _generator() -> AsyncIterator[str]:
        try:
            async for item in enforced:
                yield _format_sse(item)
        except AccessDeniedError as exc:
            yield _format_sse({"type": "ACCESS_DENIED", "reason": getattr(exc, "reason", None)})

    return StreamingHttpResponse(_generator(), content_type="text/event-stream")


def sse_rendered(func: Callable) -> Callable:
    """Wrap a view that returns an enforced stream so it responds with SSE."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> StreamingHttpResponse:
        return sse_response(func(*args, **kwargs))

    return wrapper
