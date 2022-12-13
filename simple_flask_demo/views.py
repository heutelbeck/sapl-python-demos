import random

from flask import Blueprint, typing as ft
from flask.views import View, MethodView
from sapl_base.decorators import pre_enforce, post_enforce, pre_and_post_enforce

bp = Blueprint('views', __name__, url_prefix='/')


@bp.route('/pre_enforce/POST/<int:data_id>', methods=['POST'])
@pre_enforce
def pre_enforce_sample(data_id):
    """
    pre_enforce decorator is used to enforce a function, before it is called.

    The SAPL decorator needs to be the first decorator, because it does inspection of the decorated function, if it were
    not the first decorator, it would do inspection of the previous decorator, which could result in wrong
    AuthorizationSubscriptions, resulting in probably wrong Decisions from the PDP Server.

    In this example it checks if the requesting user has permission to request specific data.
    There are 3 cases for a call to this endpoint.

    Unauthorized users are not permitted to request any data.
    User with the name 'John' has access to data in the range from 0 to 10
    User with the name 'Julia' has access to data with value >10

    If the User 'John' tries to access data outside the permitted range, a Constraint is added to the DENY Decision,
    which maps the PermissionDenied Exception to a ValueError Exception to trigger the ErrorHandler for a ValueError
    """
    return f'You have permission to see the data with the value {data_id}'


@bp.route('/post_enforce/POST', methods=['POST'])
@post_enforce
def post_enforce_sample():
    """
    post_enforce decorator is used to check if the requesting client has permission to receive the result of the
    executed function. This decorator can be used, if it can't be determined, if the user has access to the data before
    the function is executed.

    The SAPL decorator needs to be the first decorator, because it does inspection of the decorated function, if it were
    not the first decorator, it would do inspection of the previous decorator, which could result in wrong
    AuthorizationSubscriptions, resulting in probably wrong Decisions from the PDP Server.

    A function could for example retrieve data from a database, but it needs to be determined if the requesting user is
    allowed to see these data. In this example a policy denies access to certain users for even, or uneven numbers.

    In this view, 'John' is allowed to see even numbers and 'Julia' is allowed to see uneven numbers.
    """
    random_number = random.randint(1, 10)
    if random_number % 2 == 1:
        return 'uneven'
    return 'even'


@bp.route('/pre_and_post_enforce/POST/<int:data_id>', methods=['POST'])
@pre_and_post_enforce
def pre_and_post_enforce_sample(data_id):
    """
    The decorator pre_and_post_enforce is a combination of both decorator.

    The SAPL decorator needs to be the first decorator, because it does inspection of the decorated function, if it were
    not the first decorator, it would do inspection of the previous decorator, which could result in wrong
    AuthorizationSubscriptions resulting in wrong Decisions from the PDP.

    An example could be a function, which is expensive, but it can't be determined, if the requesting client is allowed
    to see the result.
    To prevent, that the function is executed on every request, a pre_and_post_enforce decorator could
    already filter requests based on arguments, which are known before the function is executed.

    This example is a combination of both previous examples.
    Unauthorized Requests are always denied.
    'Julia' has permission for requests with a value >10 and can receive a result of an uneven number
    'John' has Permission for requests in the range 0 to 10 and can receive a result of an even number
    """
    random_number = random.randint(1, 10)
    if random_number % 2 == 1:
        return 'uneven'
    return 'even'
