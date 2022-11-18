import logging

from sapl_base.constraint_handling.constraint_handler_provider import ErrorConstraintHandlerProvider


class LogErrorConstraintHandler(ErrorConstraintHandlerProvider):
    def handle(self, exception: Exception) -> Exception:
        """
        Log the given Exception as an error

        @param exception: An Exception which should be logged as an error
        @return: The exception which was provided without modification
        """
        logging.error(exception.__str__())
        return exception

    def priority(self) -> int:
        return 0

    def is_responsible(self, constraint) -> bool:
        """
        This ConstraintHandlerProvider is responsible, when the constraint is a string equalling to
        'log_error'

        @param constraint: Constraint received from the pdp as part of the Decision
        @return: If this ConstraintHandlerProvider is responsible for the given constraint
        """
        try:
            if constraint == 'log_error':
                return True
        finally:
            return False
