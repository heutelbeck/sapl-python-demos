"""Render an enforced item stream as server-sent events.

`sse_response` drives the enforced async iterator on a private event loop:
permitted items become `data:` frames, `AccessGrantedSignal` / `AccessSuspendedSignal`
become boundary frames, and `AccessDeniedError` becomes a final `ACCESS_DENIED` frame.
`sse_rendered` adapts a handler that returns such an iterator into one that responds SSE.
"""

from __future__ import annotations

import asyncio
import functools
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from flask import Response

from sapl_base.pep import AccessDeniedError, AccessGrantedSignal, AccessSuspendedSignal


def _format_sse(data: Any) -> str:
    if isinstance(data, AccessSuspendedSignal):
        return "data: " + json.dumps({"type": "ACCESS_SUSPENDED"}) + "\n\n"
    if isinstance(data, AccessGrantedSignal):
        return "data: " + json.dumps({"type": "ACCESS_GRANTED"}) + "\n\n"
    if isinstance(data, dict):
        return f"data: {json.dumps(data)}\n\n"
    return f"data: {data}\n\n"


def sse_response(enforced: AsyncIterator[Any]) -> Response:
    """Render an enforced item stream as server-sent events (Flask sync bridge)."""

    def _generator() -> Any:
        loop = asyncio.new_event_loop()
        try:
            iterator = enforced.__aiter__()
            while True:
                try:
                    item = loop.run_until_complete(iterator.__anext__())
                except StopAsyncIteration:
                    break
                except AccessDeniedError as exc:
                    yield _format_sse({"type": "ACCESS_DENIED", "reason": getattr(exc, "reason", None)})
                    break
                yield _format_sse(item)
        finally:
            loop.close()

    return Response(_generator(), mimetype="text/event-stream")


def sse_rendered(func: Callable) -> Callable:
    """Wrap a handler that returns an enforced stream so it responds with SSE."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Response:
        return sse_response(func(*args, **kwargs))

    return wrapper
