from flask_demo.singledb import db


class BankTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer, nullable=False)
    receiver = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
