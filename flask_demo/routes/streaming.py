"""SSE streaming enforcement endpoints.

The three endpoints share resource `heartbeat` and differ only by action and the
`signal_transitions` flag:

  * till-denied         -> action stream:terminate; DENY terminates with ACCESS_DENIED.
  * silent-suspending   -> action stream:suspend; SUSPEND drops items silently; PERMIT resumes.
  * observed-suspending -> action stream:suspend + signal_transitions=True; SUSPEND emits
                           ACCESS_SUSPENDED, return to Permitting emits ACCESS_GRANTED.

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
from flask import Blueprint

from sapl_flask.decorators import stream_enforce

log = structlog.get_logger()

streaming_bp = Blueprint("streaming", __name__)


async def _heartbeat_source() -> AsyncIterator[dict[str, Any]]:
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


@streaming_bp.route("/heartbeat/till-denied")
@stream_enforce(action="stream:terminate", resource="heartbeat")
def heartbeat_till_denied():
    """DENY terminates the stream with an `ACCESS_DENIED` SSE frame.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/till-denied
    """
    return _heartbeat_source()


@streaming_bp.route("/heartbeat/silent-suspending")
@stream_enforce(
    action="stream:suspend",
    resource="heartbeat",
    pause_rap_during_suspend=True,
)
def heartbeat_silent_suspending():
    """SUSPEND drops items silently; PERMIT resumes the stream. No boundary frames.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/silent-suspending
    """
    return _heartbeat_source()


@streaming_bp.route("/heartbeat/observed-suspending")
@stream_enforce(
    action="stream:suspend",
    resource="heartbeat",
    signal_transitions=True,
    pause_rap_during_suspend=True,
)
def heartbeat_observed_suspending():
    """Boundary signals: `ACCESS_SUSPENDED` on enter Suspended, `ACCESS_GRANTED` on resume.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/observed-suspending
    """
    return _heartbeat_source()
