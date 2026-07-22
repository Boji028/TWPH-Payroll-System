from datetime import datetime
from app.extensions import db


class Attendance(db.Model):
    """One row per employee per work day. Only strictly required for
    'daily' and 'hourly' pay types — monthly-salary employees can use this
    just to log absences/leaves if desired."""

    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)

    time_in = db.Column(db.Time)
    time_out = db.Column(db.Time)
    hours_worked = db.Column(db.Numeric(5, 2), default=0)
    overtime_hours = db.Column(db.Numeric(5, 2), default=0)

    status = db.Column(db.String(20), default="present")  # 'present', 'absent', 'leave', 'holiday'
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("employee_id", "date", name="uq_employee_date"),
    )

    def __repr__(self):
        return f"<Attendance emp={self.employee_id} {self.date} {self.status}>"
