from flask import render_template, Blueprint
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sapl_base.decorators import pre_enforce
from wtforms import PasswordField, SubmitField, StringField
from wtforms.validators import InputRequired, Length

from flask_demo.models.bank_account import Bankaccount
from flask_demo.models.user import User
from flask_demo.singledb import db

bp = Blueprint('overviews', __name__, url_prefix='/')


@bp.route('/bankaccount/<bankid>', methods=['GET', 'POST'])
@login_required
@pre_enforce
def bankaccount(bankid):
    account = db.session.query(Bankaccount).filter_by(id=bankid).first()
    form = PowerOfAttorneyForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(username=form.username.data).first()
        vollmachten = eval(user.vollmachten)
        vollmachten.append(str(bankid))
        vollmachten.sort()
        user.vollmachten = str(vollmachten)
        db.session.commit()
    return render_template('bankaccount.html', user=current_user, bankaccount=account, form=form)


@bp.route('/')
@login_required
def account_overview():
    bankaccounts = eval(current_user.vollmachten)
    bankaccounts.append(str(current_user.id))
    bankaccounts.sort()
    accounts = db.session.query(Bankaccount).filter(Bankaccount.id.in_(bankaccounts)).all()
    bankaccount = db.session.query(Bankaccount).filter_by(id=current_user.id).first()
    return render_template('account_overview.html', bankaccounts=accounts, user=current_user, bankaccount=bankaccount)


class PowerOfAttorneyForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=1, max=80)])
    submit = SubmitField('Grant power of attorney')
