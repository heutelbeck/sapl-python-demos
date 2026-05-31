"""EnrichErrorHandler: ERROR mapper that appends a support URL to errors."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import ERROR, ScopedHandler

log = structlog.get_logger()


class EnrichErrorHandler:
    """Transforms errors by appending a support URL."""

    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "enrichError":
            return ()
        support_url = constraint.get("supportUrl", "https://support.example.com")

        def handler(error: BaseException) -> BaseException:
            log.info(
                "[ERROR-ENRICH] Enriching error with support URL: %s",
                support_url,
                handler="EnrichErrorHandler",
            )
            enriched: BaseException = type(error)(f"{error} | Support: {support_url}")
            enriched.__cause__ = error
            return enriched

        return (ScopedHandler(signal=ERROR, priority=0, shape="mapper", handler=handler),)
