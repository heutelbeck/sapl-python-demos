"""SSE streaming enforcement endpoints (Tornado).

The three endpoints share resource `heartbeat` and differ only by action and the
`signal_transitions` flag:

  * till-denied         -> action stream:terminate; DENY terminates with ACCESS_DENIED.
  * silent-suspending   -> action stream:suspend; SUSPEND drops items silently; PERMIT resumes.
  * observed-suspending -> action stream:suspend + signal_transitions=True; SUSPEND emits
                           ACCESS_SUSPENDED, return to Permitting emits ACCESS_RESTORED.
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
    @stream_enforce(action="stream:terminate", resource="heartbeat")
    async def get(self):
        return _heartbeat_source()


class HeartbeatSilentSuspendingHandler(tornado.web.RequestHandler):
    @stream_enforce(
        action="stream:suspend",
        resource="heartbeat",
        pause_rap_during_suspend=True,
    )
    async def get(self):
        return _heartbeat_source()


class HeartbeatObservedSuspendingHandler(tornado.web.RequestHandler):
    @stream_enforce(
        action="stream:suspend",
        resource="heartbeat",
        signal_transitions=True,
        pause_rap_during_suspend=True,
    )
    async def get(self):
        return _heartbeat_source()


StreamingHandlers = [
    (r"/api/streaming/heartbeat/till-denied", HeartbeatTillDeniedHandler),
    (r"/api/streaming/heartbeat/silent-suspending", HeartbeatSilentSuspendingHandler),
    (r"/api/streaming/heartbeat/observed-suspending", HeartbeatObservedSuspendingHandler),
]
