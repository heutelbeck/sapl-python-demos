import logging

from sapl_base.constraint_handling.constraint_handler_provider import ErrorConstraintHandlerProvider


class LogErrorConstraintHandler(ErrorConstraintHandlerProvider):
    def handle(self, exception: Exception) -> Exception:
        logging.error(exception.__str__())
        return exception

    def priority(self) -> int:
        return 1

    def is_responsible(self, constraint) -> bool:
        try:
            if constraint == 'log_error':
                return True
        finally:
            return False
