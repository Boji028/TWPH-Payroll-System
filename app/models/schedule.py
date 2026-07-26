# app/models/schedule.py
from datetime import datetime, time, timedelta
from enum import Enum

from app.extensions import db


class ShiftType(str, Enum):
    OPENING = "opening"
    CLOSING = "closing"


SHIFT_LABELS = {
    ShiftType.OPENING: "Opening",
    ShiftType.CLOSING: "Closing",
}

WEEKDAY_LABELS = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}


def week_start_for(d):
    """Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())

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


class WeeklyShiftAssignment(db.Model):
    """One employee's shift + rest day for one Monday-start week. Source of
    truth for the weekly schedule view and for durable per-week overrides.
    The rotation script and the admin edit route both write here, then
    expand the *working* days into ScheduledShift rows - the rest_day date
    deliberately gets no ScheduledShift row, which is what keeps it out of
    absence scoring in biometric_import_service._derive_status. See
    app/services/schedule_rotation_service.py."""

    __tablename__ = "weekly_shift_assignments"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, index=True)
    week_start_date = db.Column(db.Date, nullable=False)  # always a Monday
    shift_type = db.Column(db.Enum(ShiftType), nullable=False)
    rest_day = db.Column(db.Integer, nullable=False)  # 0-6, this week's rest day
    is_override = db.Column(db.Boolean, nullable=False, default=False)
    # True = admin hand-edited this week; the rotation script must skip it entirely.

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = db.relationship(
        "Employee",
        backref=db.backref("weekly_shift_assignments", lazy="dynamic", cascade="all, delete-orphan"),
    )
    created_by = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("employee_id", "week_start_date", name="uq_employee_week"),
    )

    @property
    def shift_label(self):
        return SHIFT_LABELS.get(self.shift_type, self.shift_type)

    @property
    def rest_day_label(self):
        return WEEKDAY_LABELS.get(self.rest_day, self.rest_day)

    def __repr__(self):
        return f"<WeeklyShiftAssignment emp={self.employee_id} week={self.week_start_date} {self.shift_type}>"
