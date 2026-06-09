"""Streaming enforcement endpoints.

Controller-layer endpoints carry `@stream_enforce` on the handler and render with
`@sse_rendered`. The service-layer endpoint under `/api/services` delegates to a
`@stream_enforce`-decorated service method and renders with `sse_response`. The
three controller variants share resource `heartbeat`; the policy
`streaming-heartbeat-time-based.sapl` permits in [0, 20) and [40, 60), denies
`stream:terminate` in [20, 40), and suspends `stream:suspend` in [20, 40).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint

from sapl_flask.decorators import stream_enforce

from services import patient_service
from sse import sse_rendered, sse_response

streaming_bp = Blueprint("streaming", __name__)


async def _heartbeat_source() -> AsyncIterator[dict[str, Any]]:
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


@streaming_bp.route("/api/streaming/heartbeat/till-denied")
@sse_rendered
@stream_enforce(action="stream:terminate", resource="heartbeat")
def heartbeat_till_denied():
    """DENY terminates the stream with an `ACCESS_DENIED` frame."""
    return _heartbeat_source()


@streaming_bp.route("/api/streaming/heartbeat/silent-suspending")
@sse_rendered
@stream_enforce(action="stream:suspend", resource="heartbeat", pause_rap_during_suspend=True)
def heartbeat_silent_suspending():
    """SUSPEND drops items silently; PERMIT resumes. No boundary frames."""
    return _heartbeat_source()


@streaming_bp.route("/api/streaming/heartbeat/observed-suspending")
@sse_rendered
@stream_enforce(action="stream:suspend", resource="heartbeat", signal_transitions=True, pause_rap_during_suspend=True)
def heartbeat_observed_suspending():
    """Boundary frames: ACCESS_SUSPENDED on enter Suspended, ACCESS_GRANTED on resume."""
    return _heartbeat_source()


@streaming_bp.route("/api/services/streaming/heartbeat/observed-suspending")
def service_heartbeat_observed_suspending():
    """Service-layer streaming: enforcement is on the PatientService method."""
    return sse_response(patient_service.stream_heartbeat())
