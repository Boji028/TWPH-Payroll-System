from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """Staff/admin accounts that log in to operate the payroll system.
    Distinct from Employee — an Employee is who gets PAID, a User is who
    can LOG IN to run payroll. An owner or HR staffer would have both.

    role: 'owner', 'hr', 'staff' can access the admin panel (see
    app.decorators.staff_required). 'employee' logs in to self-service
    only, scoped to the linked Employee via employee_id."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="staff")  # "owner", "hr", "staff", "employee"
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), unique=True, nullable=True)
    employee = db.relationship("Employee", backref=db.backref("user_account", uselist=False))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
