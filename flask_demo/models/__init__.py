from flask_demo.singledb import db
import flask_demo.models.user
import flask_demo.models.bank_transaction
import flask_demo.models.bank_account
import flask_demo.models.credit_request
db.create_all()
db.session.commit()


