"""SSE streaming enforcement endpoints.

Demonstrates the three SAPL streaming enforcement strategies:
  1. EnforceTillDenied -- terminates permanently on first DENY
  2. EnforceDropWhileDenied -- silently drops events during DENY, resumes on PERMIT
  3. EnforceRecoverableIfDenied -- sends suspend/restore signals on policy changes

All three emit a heartbeat every 2 seconds. The PDP policy
streaming-heartbeat-time-based cycles PERMIT/DENY based on the current second
(0-19 permit, 20-39 deny, 40-59 permit).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import structlog
import tornado.web

from sapl_base.types import AuthorizationDecision
from sapl_tornado.decorators import (
    enforce_drop_while_denied,
    enforce_recoverable_if_denied,
    enforce_till_denied,
)

log = structlog.get_logger()


async def _heartbeat_source() -> AsyncIterator[dict[str, Any]]:
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


def _on_deny(decision: AuthorizationDecision) -> dict[str, Any]:
    return {"type": "ACCESS_DENIED", "message": "Stream terminated by policy"}


def _on_suspend(decision: AuthorizationDecision) -> dict[str, Any]:
    return {"type": "ACCESS_SUSPENDED", "message": "Waiting for re-authorization"}


def _on_recover(decision: AuthorizationDecision) -> dict[str, Any]:
    return {"type": "ACCESS_RESTORED", "message": "Authorization restored"}


class HeartbeatTillDeniedHandler(tornado.web.RequestHandler):
    """EnforceTillDenied -- stream terminates permanently on first DENY."""

    @enforce_till_denied(action="stream:heartbeat", resource="heartbeat", on_stream_deny=_on_deny)
    async def get(self):
        return _heartbeat_source()


class HeartbeatDropWhileDeniedHandler(tornado.web.RequestHandler):
    """EnforceDropWhileDenied -- silently drops events during DENY periods."""

    @enforce_drop_while_denied(action="stream:heartbeat", resource="heartbeat")
    async def get(self):
        return _heartbeat_source()


class HeartbeatTerminatedByCallbackHandler(tornado.web.RequestHandler):
    """EnforceRecoverableIfDenied with onStreamDeny only (no recover callback)."""

    @enforce_recoverable_if_denied(action="stream:heartbeat", resource="heartbeat", on_stream_deny=_on_suspend)
    async def get(self):
        return _heartbeat_source()


class HeartbeatDropWithCallbacksHandler(tornado.web.RequestHandler):
    """EnforceDropWhileDenied without callbacks."""

    @enforce_drop_while_denied(action="stream:heartbeat", resource="heartbeat")
    async def get(self):
        return _heartbeat_source()


class HeartbeatRecoverableHandler(tornado.web.RequestHandler):
    """EnforceRecoverableIfDenied -- sends suspend/restore signals."""

    @enforce_recoverable_if_denied(
        action="stream:heartbeat",
        resource="heartbeat",
        on_stream_deny=_on_suspend,
        on_stream_recover=_on_recover,
    )
    async def get(self):
        return _heartbeat_source()


StreamingHandlers = [
    (r"/api/streaming/heartbeat/till-denied", HeartbeatTillDeniedHandler),
    (r"/api/streaming/heartbeat/drop-while-denied", HeartbeatDropWhileDeniedHandler),
    (r"/api/streaming/heartbeat/terminated-by-callback", HeartbeatTerminatedByCallbackHandler),
    (r"/api/streaming/heartbeat/drop-with-callbacks", HeartbeatDropWithCallbacksHandler),
    (r"/api/streaming/heartbeat/recoverable", HeartbeatRecoverableHandler),
]
