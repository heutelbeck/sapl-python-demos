"""Streaming enforcement endpoints (Tornado).

Controller-layer handlers carry `@stream_enforce` on an enforced source method and
render the enforced stream with `sse_write` in `get`. The service-layer handler
delegates to a `@stream_enforce`-decorated service method. The three controller
variants share resource `heartbeat`; the policy `streaming-heartbeat-time-based.sapl`
permits in [0, 20) and [40, 60), denies `stream:terminate` in [20, 40), and suspends
`stream:suspend` in [20, 40).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import tornado.web

from sapl_tornado.decorators import stream_enforce

from services import patient_service
from sse import sse_write


async def _heartbeat_source() -> AsyncIterator[dict[str, Any]]:
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


class HeartbeatTillDeniedHandler(tornado.web.RequestHandler):
    @stream_enforce(action="stream:terminate", resource="heartbeat")
    async def _enforced(self):
        return _heartbeat_source()

    async def get(self):
        await sse_write(self, self._enforced())


class HeartbeatSilentSuspendingHandler(tornado.web.RequestHandler):
    @stream_enforce(action="stream:suspend", resource="heartbeat", pause_rap_during_suspend=True)
    async def _enforced(self):
        return _heartbeat_source()

    async def get(self):
        await sse_write(self, self._enforced())


class HeartbeatObservedSuspendingHandler(tornado.web.RequestHandler):
    @stream_enforce(action="stream:suspend", resource="heartbeat", signal_transitions=True, pause_rap_during_suspend=True)
    async def _enforced(self):
        return _heartbeat_source()

    async def get(self):
        await sse_write(self, self._enforced())


class ServiceHeartbeatObservedSuspendingHandler(tornado.web.RequestHandler):
    async def get(self):
        await sse_write(self, patient_service.stream_heartbeat())


StreamingHandlers = [
    (r"/api/streaming/heartbeat/till-denied", HeartbeatTillDeniedHandler),
    (r"/api/streaming/heartbeat/silent-suspending", HeartbeatSilentSuspendingHandler),
    (r"/api/streaming/heartbeat/observed-suspending", HeartbeatObservedSuspendingHandler),
    (r"/api/services/streaming/heartbeat/observed-suspending", ServiceHeartbeatObservedSuspendingHandler),
]
