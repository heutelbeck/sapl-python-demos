"""SSE streaming enforcement endpoints (Tornado).

All three endpoints use the same `@stream_enforce` decorator with different
flag combinations:

  * till-denied            -> defaults; DENY terminates with ACCESS_DENIED.
  * drop-while-denied      -> pause_rap_during_suspend=True; SUSPEND drops items
                              silently; PERMIT resumes.
  * recoverable            -> signal_transitions=True + pause_rap_during_suspend=True;
                              SUSPEND emits ACCESS_SUSPENDED, return to Permitting
                              emits ACCESS_RESTORED.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import structlog
import tornado.web

from sapl_tornado.decorators import stream_enforce

log = structlog.get_logger()


async def _heartbeat_source() -> AsyncIterator[dict[str, Any]]:
    """Infinite heartbeat generator emitting every 2 seconds."""
    seq = 0
    while True:
        yield {"seq": seq, "ts": datetime.now(timezone.utc).isoformat()}
        seq += 1
        await asyncio.sleep(2)


class HeartbeatTillDeniedHandler(tornado.web.RequestHandler):
    @stream_enforce(action="stream:heartbeat", resource="heartbeat")
    async def get(self):
        return _heartbeat_source()


class HeartbeatDropWhileDeniedHandler(tornado.web.RequestHandler):
    @stream_enforce(
        action="stream:heartbeat",
        resource="heartbeat-suspendable",
        pause_rap_during_suspend=True,
    )
    async def get(self):
        return _heartbeat_source()


class HeartbeatRecoverableHandler(tornado.web.RequestHandler):
    @stream_enforce(
        action="stream:heartbeat",
        resource="heartbeat-suspendable",
        signal_transitions=True,
        pause_rap_during_suspend=True,
    )
    async def get(self):
        return _heartbeat_source()


StreamingHandlers = [
    (r"/api/streaming/heartbeat/till-denied", HeartbeatTillDeniedHandler),
    (r"/api/streaming/heartbeat/drop-while-denied", HeartbeatDropWhileDeniedHandler),
    (r"/api/streaming/heartbeat/recoverable", HeartbeatRecoverableHandler),
]
