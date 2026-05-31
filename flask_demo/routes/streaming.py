"""SSE streaming enforcement endpoints.

All three endpoints use the same `@stream_enforce` decorator with different
flag combinations:

  * till-denied            -> defaults; DENY terminates with ACCESS_DENIED.
  * drop-while-denied      -> pause_rap_during_suspend=True; SUSPEND drops
                              items silently; PERMIT resumes.
  * recoverable            -> signal_transitions=True + pause_rap_during_suspend=True;
                              SUSPEND emits ACCESS_SUSPENDED, return to
                              Permitting emits ACCESS_RESTORED.

The cycle PERMIT -> SUSPEND -> PERMIT is driven by the policies
`streaming-heartbeat-till-denied.sapl` (emits DENY in the window) and
`streaming-heartbeat-suspendable.sapl` (emits SUSPEND in the window).
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
@stream_enforce(action="stream:heartbeat", resource="heartbeat")
def heartbeat_till_denied():
    """DENY terminates the stream with an `ACCESS_DENIED` SSE frame.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/till-denied
    """
    return _heartbeat_source()


@streaming_bp.route("/heartbeat/drop-while-denied")
@stream_enforce(
    action="stream:heartbeat",
    resource="heartbeat-suspendable",
    pause_rap_during_suspend=True,
)
def heartbeat_drop_while_denied():
    """SUSPEND drops items silently; PERMIT resumes the stream.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/drop-while-denied
    """
    return _heartbeat_source()


@streaming_bp.route("/heartbeat/recoverable")
@stream_enforce(
    action="stream:heartbeat",
    resource="heartbeat-suspendable",
    signal_transitions=True,
    pause_rap_during_suspend=True,
)
def heartbeat_recoverable():
    """Boundary signals: `ACCESS_SUSPENDED` on enter Suspended, `ACCESS_RESTORED` on resume.

    Connect with: curl -N http://localhost:3000/api/streaming/heartbeat/recoverable
    """
    return _heartbeat_source()
