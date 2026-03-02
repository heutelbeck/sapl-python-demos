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
from fastapi import APIRouter, Request

from sapl_base.types import AuthorizationDecision
from sapl_fastapi.decorators import (
    enforce_drop_while_denied,
    enforce_recoverable_if_denied,
    enforce_till_denied,
)

log = structlog.get_logger()

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


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


@router.get("/heartbeat/till-denied")
@enforce_till_denied(
    action="stream:heartbeat",
    resource="heartbeat",
    on_stream_deny=_on_deny,
)
async def heartbeat_till_denied(request: Request):
    """EnforceTillDenied -- stream terminates permanently on first DENY.

    The onStreamDeny callback sends a final ACCESS_DENIED event before
    the stream completes. Once denied, the client must reconnect.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/till-denied
    """
    return _heartbeat_source()


@router.get("/heartbeat/drop-while-denied")
@enforce_drop_while_denied(
    action="stream:heartbeat",
    resource="heartbeat",
)
async def heartbeat_drop_while_denied(request: Request):
    """EnforceDropWhileDenied -- silently drops events during DENY periods.

    The client sees gaps in sequence numbers but the stream stays open.
    Events resume automatically when the PDP re-permits.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/drop-while-denied
    """
    return _heartbeat_source()


@router.get("/heartbeat/terminated-by-callback")
@enforce_recoverable_if_denied(
    action="stream:heartbeat",
    resource="heartbeat",
    on_stream_deny=_on_suspend,
)
async def heartbeat_terminated_by_callback(request: Request):
    """EnforceRecoverableIfDenied with onStreamDeny only (no recover callback).

    On DENY: sends ACCESS_SUSPENDED event. The stream stays alive and
    resumes forwarding data on re-PERMIT, but no explicit restore signal
    is sent.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/terminated-by-callback
    """
    return _heartbeat_source()


@router.get("/heartbeat/drop-with-callbacks")
@enforce_drop_while_denied(
    action="stream:heartbeat",
    resource="heartbeat",
)
async def heartbeat_drop_with_callbacks(request: Request):
    """EnforceDropWhileDenied without callbacks.

    Silently drops events during DENY periods. No deny/recover signals
    are sent. The stream stays alive and resumes forwarding on re-PERMIT.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/drop-with-callbacks
    """
    return _heartbeat_source()


@router.get("/heartbeat/recoverable")
@enforce_recoverable_if_denied(
    action="stream:heartbeat",
    resource="heartbeat",
    on_stream_deny=_on_suspend,
    on_stream_recover=_on_recover,
)
async def heartbeat_recoverable(request: Request):
    """EnforceRecoverableIfDenied -- sends suspend/restore signals.

    On DENY: sends an ACCESS_SUSPENDED event.
    On re-PERMIT: sends an ACCESS_RESTORED event.
    The client can show UI status changes based on these signals.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/recoverable
    """
    return _heartbeat_source()
