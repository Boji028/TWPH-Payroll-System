# app/models/schedule.py
from datetime import datetime, time
from enum import Enum

from app.extensions import db


class ShiftType(str, Enum):
    OPENING = "opening"
    CLOSING = "closing"


SHIFT_LABELS = {
    ShiftType.OPENING: "Opening",
    ShiftType.CLOSING: "Closing",
}

# Fixed shift hours for Travel Worthy PH. Add another entry here (and to
# the <select> in schedule/log.html) if the business introduces a new
# shift type later - deliberately not a separate editable table for just
# two fixed values.
SHIFT_HOURS = {
    ShiftType.OPENING: (time(8, 0), time(18, 0)),
    ShiftType.CLOSING: (time(11, 30), time(20, 0)),
}


class ScheduledShift(db.Model):
    """One employee's shift assignment for one day. Forward-looking and
    independent of Attendance (which records what actually happened) and
    of payroll - same "record only, no automatic effect" treatment as
    LeaveRequest. One shift per employee per day, enforced at the DB
    level via uq_employee_schedule_date."""

    __tablename__ = "scheduled_shifts"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.Enum(ShiftType), nullable=False)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    employee = db.relationship(
        "Employee",
        backref=db.backref("scheduled_shifts", lazy="dynamic", cascade="all, delete-orphan"),
    )
    created_by = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("employee_id", "date", name="uq_employee_schedule_date"),
    )

    @property
    def shift_label(self):
        return SHIFT_LABELS.get(self.shift_type, self.shift_type)

    @property
    def start_time(self):
        return SHIFT_HOURS[self.shift_type][0]

    @property
    def end_time(self):
        return SHIFT_HOURS[self.shift_type][1]

    def __repr__(self):
        return f"<ScheduledShift emp={self.employee_id} {self.date} {self.shift_type}>"
