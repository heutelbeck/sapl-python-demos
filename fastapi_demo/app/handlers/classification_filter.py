"""FilterPredicateConstraintHandlerProvider -- ClassificationFilterHandler.

Handles obligations/advice of type "filterByClassification".
When the endpoint returns a list, this handler filters out elements whose
classification level exceeds the allowed maximum.

Each element is expected to have a "classification" field.
Elements without a classification are excluded (fail-closed).

Policy obligation example:
  { "type": "filterByClassification", "maxLevel": "INTERNAL" }
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

log = structlog.get_logger()

_CLASSIFICATION_LEVELS: dict[str, int] = {
    "PUBLIC": 0,
    "INTERNAL": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
}


class ClassificationFilterHandler:
    """Filters list elements by classification level."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "filterByClassification"

    def get_handler(self, constraint: Any) -> Callable[[Any], bool]:
        max_level = constraint.get("maxLevel", "PUBLIC")
        max_rank = _CLASSIFICATION_LEVELS.get(max_level, 0)

        def predicate(element: Any) -> bool:
            if not isinstance(element, dict):
                return False
            element_level = element.get("classification")
            element_rank = _CLASSIFICATION_LEVELS.get(element_level)
            if element_rank is None:
                log.warning(
                    "[FILTER] Element excluded: unknown classification",
                    classification=element_level,
                    handler="ClassificationFilterHandler",
                )
                return False
            allowed = element_rank <= max_rank
            if not allowed:
                log.info(
                    "[FILTER] Excluded %s element (max: %s)",
                    element_level,
                    max_level,
                    handler="ClassificationFilterHandler",
                )
            return allowed

        return predicate
