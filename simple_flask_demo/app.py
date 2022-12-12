import json

from flask import Flask
from sapl_base.exceptions import PermissionDenied

from simple_flask_demo import error_handler
from subject_functions import jwt_as_subject

app = Flask(__name__)


if __name__ == '__main__':
    app.config.from_file("config.json", load=json.load)
    "Import sapl_flask and init the package with the configuration and the subject functions"
    import sapl_flask
    sapl_flask.init_sapl(app.config,[jwt_as_subject])

    "Import the package, which contains the ConstraintHandlerProvider and init the ConstraintHandlerService"
    import constraint_handler
    constraint_handler.init_constraint_handler_service()

    "Register views and errorhandler"
    import views
    app.register_blueprint(views.bp)
    app.register_error_handler(PermissionDenied,error_handler.permission_denied)
    app.register_error_handler(ValueError,error_handler.value_error)

    app.run()
