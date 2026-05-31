"""NotifyOnErrorHandler: ERROR consumer for `notifyOnError` obligations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import ERROR, ScopedHandler

log = structlog.get_logger()


class NotifyOnErrorHandler:
    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "notifyOnError":
            return ()

        def handler(error: BaseException) -> None:
            log.warning(
                "[ERROR-NOTIFY] Error during policy-protected operation: %s",
                str(error),
                handler="NotifyOnErrorHandler",
            )

        return (ScopedHandler(signal=ERROR, priority=0, shape="consumer", handler=handler),)
