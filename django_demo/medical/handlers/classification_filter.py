"""ClassificationFilterHandler: OUTPUT mapper that filters list elements by classification."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import OUTPUT, ScopedHandler

log = structlog.get_logger()

_CLASSIFICATION_LEVELS: dict[str, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
}


class ClassificationFilterHandler:
    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "filterByClassification":
            return ()
        max_level = constraint.get("maxLevel", "PUBLIC")
        max_rank = _CLASSIFICATION_LEVELS.get(max_level, 0)

        def handler(value: Any) -> Any:
            if not isinstance(value, list):
                return value
            kept: list[Any] = []
            for element in value:
                if not isinstance(element, dict):
                    continue
                element_level = element.get("classification")
                element_rank = _CLASSIFICATION_LEVELS.get(element_level)
                if element_rank is None:
                    log.warning(
                        "[FILTER] Element excluded: unknown classification",
                        classification=element_level,
                        handler="ClassificationFilterHandler",
                    )
                    continue
                if element_rank <= max_rank:
                    kept.append(element)
                else:
                    log.info(
                        "[FILTER] Excluded %s element (max: %s)",
                        element_level, max_level,
                        handler="ClassificationFilterHandler",
                    )
            return kept

        return (ScopedHandler(signal=OUTPUT, priority=10, shape="mapper", handler=handler),)
