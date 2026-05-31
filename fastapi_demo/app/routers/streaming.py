"""SSE streaming enforcement endpoints.

All three endpoints use the same `@stream_enforce` decorator with different
flag combinations:

  * till-denied            -> defaults; DENY terminates with ACCESS_DENIED.
  * drop-while-denied      -> pause_rap_during_suspend=True; SUSPEND drops items
                              silently; PERMIT resumes.
  * recoverable            -> signal_transitions=True + pause_rap_during_suspend=True;
                              SUSPEND emits ACCESS_SUSPENDED, return to Permitting
                              emits ACCESS_RESTORED.

The cycle PERMIT -> SUSPEND -> PERMIT is driven by the policies
`streaming-heartbeat-till-denied.sapl` (DENY in the window) and
`streaming-heartbeat-suspendable-*.sapl` (PERMIT and SUSPEND alternating).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Request

from sapl_fastapi.decorators import stream_enforce

log = structlog.get_logger()

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


async def _heartbeat_source() -> AsyncIterator[dict[str, Any]]:
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


@router.get("/heartbeat/till-denied")
@stream_enforce(action="stream:heartbeat", resource="heartbeat")
async def heartbeat_till_denied(request: Request):
    """DENY terminates the stream with an `ACCESS_DENIED` SSE frame."""
    return _heartbeat_source()


@router.get("/heartbeat/drop-while-denied")
@stream_enforce(
    action="stream:heartbeat",
    resource="heartbeat-suspendable",
    pause_rap_during_suspend=True,
)
async def heartbeat_drop_while_denied(request: Request):
    """SUSPEND drops items silently; PERMIT resumes the stream."""
    return _heartbeat_source()


@router.get("/heartbeat/recoverable")
@stream_enforce(
    action="stream:heartbeat",
    resource="heartbeat-suspendable",
    signal_transitions=True,
    pause_rap_during_suspend=True,
)
async def heartbeat_recoverable(request: Request):
    """Boundary signals: ACCESS_SUSPENDED on enter Suspended, ACCESS_RESTORED on resume."""
    return _heartbeat_source()
