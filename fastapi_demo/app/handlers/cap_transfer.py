"""MethodInvocationConstraintHandlerProvider -- CapTransferHandler.

Handles obligations of type "capTransferAmount".
Caps the transfer amount at the policy-specified maximum.
The handler knows that the parameter is called "amount" and checks
both kwargs and positional args. If the requested amount exceeds
the limit, it is replaced with the maximum -- the endpoint function
never sees the original value.

Policy obligation example:
  { "type": "capTransferAmount", "maxAmount": 5000 }
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog

from sapl_base.constraint_types import MethodInvocationContext

log = structlog.get_logger()

_PARAM_NAME = "amount"


class CapTransferHandler:
    """Caps a numeric argument at a policy-defined maximum."""

    def is_responsible(self, constraint: Any) -> bool:
        return isinstance(constraint, dict) and constraint.get("type") == "capTransferAmount"

    def get_handler(self, constraint: Any) -> Callable[[MethodInvocationContext], None]:
        max_amount = constraint.get("maxAmount", 0)

        def handler(context: MethodInvocationContext) -> None:
            if _PARAM_NAME in context.kwargs:
                requested = float(context.kwargs[_PARAM_NAME])
                if requested > max_amount:
                    context.kwargs[_PARAM_NAME] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        function=context.function_name,
                        requested=requested,
                        capped_to=max_amount,
                    )
                return
            for i, arg in enumerate(context.args):
                if isinstance(arg, (int, float)) and arg > max_amount:
                    context.args[i] = max_amount
                    log.info(
                        "Amount capped by policy",
                        handler="CapTransferHandler",
                        function=context.function_name,
                        requested=arg,
                        capped_to=max_amount,
                    )
                    return

        return handler
