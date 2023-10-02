from flask_login import UserMixin

from flask_demo.singledb import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    relatives = db.Column(db.String(80), default="[]")
    password = db.Column(db.String(80), nullable=False)
    groups = db.Column(db.String(80), default="['user']")
    vollmachten = db.Column(db.String(80), default="[]")
