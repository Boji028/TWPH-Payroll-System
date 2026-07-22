from datetime import datetime
from app.extensions import db


class Employee(db.Model):
    """A person who gets paid. pay_type decides which fields matter:
    - 'monthly': monthly_rate is used, attendance is optional (just tracks leaves/absences)
    - 'daily': daily_rate is used, attendance hours matter
    - 'hourly': hourly_rate is used, attendance hours matter directly
    """

    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=False)  # e.g. EMP-0001
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(80))
    position = db.Column(db.String(80))

    pay_type = db.Column(db.String(10), nullable=False)  # 'monthly', 'daily', 'hourly'
    monthly_rate = db.Column(db.Numeric(12, 2))
    daily_rate = db.Column(db.Numeric(12, 2))
    hourly_rate = db.Column(db.Numeric(12, 2))

    date_hired = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="active")  # 'active', 'inactive', 'terminated'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance_records = db.relationship("Attendance", backref="employee", lazy="dynamic")
    payslips = db.relationship("Payslip", backref="employee", lazy="dynamic")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Employee {self.employee_code} {self.full_name}>"
