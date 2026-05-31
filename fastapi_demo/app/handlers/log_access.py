"""LogAccessHandler: DECISION runner for `logAccess` obligations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import DECISION, ScopedHandler

log = structlog.get_logger()


class LogAccessHandler:
    """Logs a policy-defined message on each authorization decision."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "logAccess":
            return ()
        message = constraint.get("message", "Access logged")

        def handler() -> None:
            log.info("[POLICY] %s", message, handler="LogAccessHandler")

        return (ScopedHandler(signal=DECISION, priority=0, shape="runner", handler=handler),)
