"""SSE streaming enforcement endpoints.

The three endpoints share resource `heartbeat` and differ only by action and the
`signal_transitions` flag:

  * till-denied         -> action stream:terminate; DENY terminates with ACCESS_DENIED.
  * silent-suspending   -> action stream:suspend; SUSPEND drops items silently; PERMIT resumes.
  * observed-suspending -> action stream:suspend + signal_transitions=True; SUSPEND emits
                           ACCESS_SUSPENDED, return to Permitting emits ACCESS_RESTORED.

The cycle PERMIT -> (DENY | SUSPEND) -> PERMIT is driven by the single policy
`streaming-heartbeat-time-based.sapl`, which permits in [0, 20) and [40, 60), denies
`stream:terminate` in [20, 40), and suspends `stream:suspend` in [20, 40).
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
@stream_enforce(action="stream:terminate", resource="heartbeat")
async def heartbeat_till_denied(request: Request):
    """DENY terminates the stream with an `ACCESS_DENIED` SSE frame."""
    return _heartbeat_source()


@router.get("/heartbeat/silent-suspending")
@stream_enforce(
    action="stream:suspend",
    resource="heartbeat",
    pause_rap_during_suspend=True,
)
async def heartbeat_silent_suspending(request: Request):
    """SUSPEND drops items silently; PERMIT resumes the stream. No boundary frames."""
    return _heartbeat_source()


@router.get("/heartbeat/observed-suspending")
@stream_enforce(
    action="stream:suspend",
    resource="heartbeat",
    signal_transitions=True,
    pause_rap_during_suspend=True,
)
async def heartbeat_observed_suspending(request: Request):
    """Boundary signals: ACCESS_SUSPENDED on enter Suspended, ACCESS_RESTORED on resume."""
    return _heartbeat_source()
