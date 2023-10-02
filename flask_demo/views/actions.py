from flask import redirect, url_for, flash, render_template, Blueprint, request
from flask_login import login_user, current_user, login_required
from flask_wtf import FlaskForm
from sapl_base.decorators import pre_enforce
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import InputRequired, Length

from flask_demo.models.bank_account import Bankaccount
from flask_demo.models.credit_request import CreditRequest
from flask_demo.models.user import User
from flask_demo.singledb import db
import flask_demo.database_manager as db_manager
bp = Blueprint('actions', __name__, url_prefix='/')


@bp.route('/transaction/<bankid>', methods=['GET', 'POST'])
@login_required
@pre_enforce
def transaction(bankid):
    form = TransactionForm()
    bankaccount= db.session.query(Bankaccount).filter_by(id=bankid).first()
    if form.validate_on_submit():
        db_manager.send_money(form.receiver.data,form.amount.data,bankid)
    return render_template('transaction.html',user=current_user,bankaccount=bankaccount,form=form)


@bp.route('/request_credit/<bankid>', methods=['GET', 'POST'])
@login_required
@pre_enforce
def request_credit(bankid):
    form = RequestCreditForm()
    if form.validate_on_submit():
        db_manager.request_credit(bankid,form.amount.data)
    bankaccount = db.session.query(Bankaccount).filter_by(id=bankid).first()
    return render_template('request_credit.html', form=form, bankaccount=bankaccount, user=current_user)


@bp.route('/approve_credit', methods=['GET', 'POST'])
@login_required
@pre_enforce
def approve_credit():
    if request.method == 'POST':
        credit_request = db.session.query(CreditRequest).filter_by(id=request.form.get('requestid')).first()
        db_manager.approve_credit(credit_request,credit_request.accountid)
    credit_requests = db_manager.gather_open_request()
    return render_template('approve_credit_changes.html',credit_requests=credit_requests,user=current_user)



class TransactionForm(FlaskForm):
    receiver = StringField('Receiver', validators=[InputRequired(), Length(min=4, max=80)])
    amount = IntegerField('Amount', validators=[InputRequired()])
    submit = SubmitField('Login')


class RequestCreditForm(FlaskForm):
    amount = IntegerField('Amount', validators=[InputRequired()])
    submit = SubmitField('Request')
