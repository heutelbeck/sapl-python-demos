# import logging
# from typing import Any, List
#
# from sapl_base.constraint_handling.constraint_handler_provider import ResultConstraintHandlerProvider
#
# from flask_demo.models.credit_request import CreditRequest
# from flask_login import current_user
#
# from flask_demo.models.user import User
# from flask_demo.singledb import db
#
#
# class FilterRelativesConstraintHandler(ResultConstraintHandlerProvider):
#
#     def handle(self, result: Any) -> Any:
#         accountids = [request.accountid for request in result]
#         users = db.session.query(User).filter_by(User.accountid.in_(accountids)).all()
#         accountnames = [user.username for user in users]
#         gefilterte_elemente = [request for request in result if request.accountid not in current_user.relatives]
#         return credit_request
#
#     def priority(self) -> int:
#         return 0
#
#     def is_responsible(self, constraint) -> bool:
#         return True if constraint == 'filter_relatives' else False
#
#
# class LogCreditRequests(ResultConstraintHandlerProvider):
#     def handle(self, result: Any) -> Any:
#         logging.info("")
#
#     def priority(self) -> int:
#         return 0
#
#     def is_responsible(self, constraint) -> bool:
#         return True if constraint == 'log_credit' else False
