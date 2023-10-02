from flask_demo.singledb import db

class CreditRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accountid = db.Column(db.String, nullable=False)
    current_credit = db.Column(db.Float, default=0, nullable=False)
    requested_credit = db.Column(db.Float, default=0, nullable=False)
    approved = db.Column(db.Boolean,default=False)