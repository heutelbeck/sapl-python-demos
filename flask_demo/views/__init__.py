from flask_login import LoginManager, current_user
from flask import flash, redirect
from werkzeug.exceptions import Unauthorized

from flask_demo.singledb import db
import flask_demo.models
from flask import current_app
login_manager = LoginManager()
login_manager.init_app(current_app)
import flask_demo.views.login
import flask_demo.views.overviews
import flask_demo.views.actions

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(flask_demo.models.user.User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if current_user.is_anonymous:
        flash('Please log in to access this page.', 'danger')
        return redirect(current_app.config['LOGIN_VIEW'])  # Redirect to the login view
    else:
        raise Unauthorized('Access denied. You do not have permission to access this page.')

def register_bp():
    current_app.register_blueprint(flask_demo.views.login.bp)
    current_app.register_blueprint(flask_demo.views.overviews.bp)
    current_app.register_blueprint(flask_demo.views.actions.bp)

