from flask_demo.singledb import db


class Bankaccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String, nullable=False)
    balance = db.Column(db.Float, default=0, nullable=False)
    credit = db.Column(db.Float, default=0, nullable=False)
