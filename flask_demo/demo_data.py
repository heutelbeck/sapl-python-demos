from flask_demo.models.bank_account import Bankaccount
from flask_demo.models.user import User
from flask_demo.singledb import db


def create_demo_data():
    peter = "Peter"
    if not user_exist(peter):
        user = User(username=peter, password="password", groups="['staff','user']", relatives="['Timo']")
        db.session.add(user)
        db.session.commit()
        new_account = Bankaccount(owner=peter, balance=1000, credit=1000)
        db.session.add(new_account)
        db.session.commit()
    sandra = "Sandra"
    if not user_exist(sandra):
        user = User(username=sandra, password="password", groups="['staff','user']", relatives="['Steffen']")
        db.session.add(user)
        db.session.commit()
        new_account = Bankaccount(owner=sandra, balance=1000, credit=1000)
        db.session.add(new_account)
        db.session.commit()


def user_exist(name) -> bool:
    existing_user = db.session.query(User).filter_by(username=name).first()
    if existing_user:
        return True
    return False
