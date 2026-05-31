"""LogStreamEventHandler: OUTPUT consumer for `logStreamEvent` obligations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import OUTPUT, ScopedHandler

log = structlog.get_logger()


class LogStreamEventHandler:
    """Logs streaming events as a side-effect."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "logStreamEvent":
            return ()
        message = constraint.get("message", "Stream event")

        def handler(value: Any) -> None:
            log.info("[STREAM-LOG] %s: %s", message, value, handler="LogStreamEventHandler")

        return (ScopedHandler(signal=OUTPUT, priority=30, shape="consumer", handler=handler),)
