from typing import Type

from sapl_base.constraint_handling.constraint_handler_provider import ErrorConstraintHandlerProvider


class ThrowValueErrorOnPermissionDenied(ErrorConstraintHandlerProvider):
    def handle(self, exception: Exception) -> Type[ValueError]:
        return ValueError

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        return True if constraint == 'throw_value_error_on_permission_denied'else False
