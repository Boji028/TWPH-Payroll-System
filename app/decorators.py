"""Access-control decorators shared across route blueprints."""
from functools import wraps
from flask import abort
from flask_login import current_user, login_required

STAFF_ROLES = ("owner", "hr", "staff")


def staff_required(view):
    """Allows owner/hr/staff roles only; employee-role logins get a 403.
    Includes login_required, so routes only need this one decorator."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role not in STAFF_ROLES:
            abort(403)
        return view(*args, **kwargs)
    return wrapped
