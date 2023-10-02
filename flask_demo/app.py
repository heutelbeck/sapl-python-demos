import json

from flask import Flask
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import Unauthorized

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)


def sapl_subject(values: dict):
    user = current_user
    if not current_user.is_authenticated:
        return {"anonymous"}
    subject = {}
    subject.update({"name": user.username})
    subject.update({"userid": str(user.id)})
    relatives = eval(user.relatives)
    groups = eval(user.groups)
    vollmachten = eval(user.vollmachten)
    subject.update({"relatives": relatives})
    subject.update({"groups": groups})
    subject.update({"vollmachten": vollmachten})
    return subject


if __name__ == '__main__':
    with app.app_context():
        app.config.from_file("config.json", load=json.load)
        import flask_demo.singledb as singledb

        global db
        singledb.db = SQLAlchemy(app)
        import flask_demo.models

        import demo_data

        demo_data.create_demo_data()

        import flask_demo.views

        flask_demo.views.register_bp()
        import sapl_flask

        sapl_flask.init_sapl(app.config, sapl_subject)
        import sapl_base.policy_enforcement_points.policy_enforcement_point as pep

        pep.permission_denied_exception = Unauthorized
    app.run(debug=True)
