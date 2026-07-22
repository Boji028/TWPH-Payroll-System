from datetime import datetime
from app.extensions import db


class PayrollRun(db.Model):
    """One payroll cycle (e.g. 'July 1-15, 2026'). Generates a Payslip
    per active employee when processed."""

    __tablename__ = "payroll_runs"

    id = db.Column(db.Integer, primary_key=True)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="draft")  # 'draft', 'processed', 'paid'
    date_processed = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payslips = db.relationship("Payslip", backref="payroll_run", lazy="dynamic")

    def __repr__(self):
        return f"<PayrollRun {self.period_start} to {self.period_end}>"


class Payslip(db.Model):
    """One employee's pay breakdown for one PayrollRun."""

    __tablename__ = "payslips"

    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey("payroll_runs.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)

    gross_pay = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_deductions = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    net_pay = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # Breakdown snapshot at time of processing, useful for audit trail
    base_pay = db.Column(db.Numeric(12, 2), default=0)
    overtime_pay = db.Column(db.Numeric(12, 2), default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    deductions = db.relationship("Deduction", backref="payslip", lazy="dynamic")

    def __repr__(self):
        return f"<Payslip emp={self.employee_id} run={self.payroll_run_id} net={self.net_pay}>"
