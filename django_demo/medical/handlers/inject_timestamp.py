"""InjectTimestampHandler: INPUT mapper that adds `policy_timestamp` to kwargs."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import structlog

from sapl_base.pep import INPUT, ScopedHandler

log = structlog.get_logger()


class InjectTimestampHandler:
    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "injectTimestamp":
            return ()

        def handler(value: Any) -> Any:
            args, kwargs = value
            kwargs = dict(kwargs)
            timestamp = datetime.now(timezone.utc).isoformat()
            kwargs["policy_timestamp"] = timestamp
            log.info("[METHOD] Injected policy timestamp: %s", timestamp, handler="InjectTimestampHandler")
            return (args, kwargs)

        return (ScopedHandler(signal=INPUT, priority=0, shape="mapper", handler=handler),)
