from sapl_base.decorators import pre_enforce

from flask_demo.models.bank_account import Bankaccount
from flask_demo.models.credit_request import CreditRequest
from flask_demo.singledb import db


@pre_enforce  # nur mit Vollmacht oder als Nutzer
def send_money(receivername, amount, bankid):
    sender = db.session.query(Bankaccount).filter_by(id=bankid).first()
    receiver = db.session.query(Bankaccount).filter_by(owner=receivername).first()
    sender.balance -= amount
    receiver.balance += amount
    db.session.commit()


@pre_enforce  # nur mit Vollmacht oder als Nutzer
def request_credit(bankid, amount):
    request = CreditRequest(accountid=bankid, requested_credit=amount)
    db.session.add(request)
    db.session.commit()


@pre_enforce  # nur für Staff
def approve_credit(request, accountid):
    bankaccount = db.session.query(Bankaccount).filter_by(id=accountid).first()
    bankaccount.credit += request.requested_credit
    request.approved = True
    db.session.commit()


def gather_open_request():
    return db.session.query(CreditRequest).filter_by(approved=False).all()
