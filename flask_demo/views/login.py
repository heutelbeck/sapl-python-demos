from flask import redirect, url_for, flash, render_template, Blueprint
from flask_login import login_user, current_user, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length

from flask_demo.models.bank_account import Bankaccount
from flask_demo.models.user import User
from flask_demo.singledb import db

bp = Blueprint('views', __name__, url_prefix='/')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('overviews.account_overview'))
        else:
            flash("Nutzer oder Passwort falsch")
    if current_user.is_authenticated:
        return redirect(url_for('overviews.account_overview'))
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        new_user = User(username=form.username.data, password=form.password.data)
        db.session.add(new_user)
        db.session.commit()
        new_account = Bankaccount(owner=form.username.data, balance=1000, credit=1000)
        db.session.add(new_account)
        db.session.commit()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('views.login'))

    return render_template('register.html', form=form)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=120)])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6, max=120)])
    submit = SubmitField('Register')
