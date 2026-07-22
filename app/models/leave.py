from datetime import datetime
from app.extensions import db


class LeaveRequest(db.Model):
    """A leave/time-off request submitted by an employee and reviewed by
    staff. Purely a record for now — approving a request does not affect
    payroll computation (see services/payroll_service.py). Separate from
    Attendance's existing 'leave' status, which is unrelated to this model."""

    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)

    leave_type = db.Column(db.String(20), nullable=False)  # 'vacation', 'sick', 'unpaid', 'other'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))

    status = db.Column(db.String(20), default="pending")  # 'pending', 'approved', 'rejected'
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)

    employee = db.relationship("Employee", backref=db.backref("leave_requests", lazy="dynamic"))
    reviewed_by = db.relationship("User")

    @property
    def days_requested(self):
        return (self.end_date - self.start_date).days + 1

    def __repr__(self):
        return f"<LeaveRequest emp={self.employee_id} {self.start_date}..{self.end_date} {self.status}>"
