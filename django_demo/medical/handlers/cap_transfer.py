"""CapTransferHandler: INPUT mapper that caps the `amount` argument."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from sapl_base.pep import INPUT, ScopedHandler

log = structlog.get_logger()

_PARAM_NAME = "amount"


class CapTransferHandler:
    def get_handlers(self, constraint: Any) -> Sequence[ScopedHandler]:
        if not isinstance(constraint, dict) or constraint.get("type") != "capTransferAmount":
            return ()
        max_amount = constraint.get("maxAmount", 0)

        def handler(value: Any) -> Any:
            args, kwargs = value
            kwargs = dict(kwargs)
            args = list(args)
            if _PARAM_NAME in kwargs:
                requested = float(kwargs[_PARAM_NAME])
                if requested > max_amount:
                    kwargs[_PARAM_NAME] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        requested=requested,
                        capped_to=max_amount,
                    )
                return (tuple(args), kwargs)
            for i, arg in enumerate(args):
                if isinstance(arg, (int, float)) and arg > max_amount:
                    args[i] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        requested=arg,
                        capped_to=max_amount,
                    )
                    break
            return (tuple(args), kwargs)

        return (ScopedHandler(signal=INPUT, priority=10, shape="mapper", handler=handler),)
