"""
Core payroll computation. Kept separate from routes so the math can be
tested directly (see tests/unit/) without spinning up a request.

Statutory deductions (SSS, PhilHealth, Pag-IBIG, BIR withholding tax) are
NOT implemented yet — this was left undecided during planning. When ready,
add a `calculate_statutory_deductions(employee, gross_pay)` function here
and call it inside process_payroll_run() before finalizing net_pay. Nothing
else in this file needs to change for that to slot in.
"""
from datetime import datetime
from decimal import Decimal
from app.extensions import db
from app.models.employee import Employee
from app.models.payroll import Payslip
from app.models.attendance import Attendance
from app.models.deduction import Deduction


def calculate_gross_pay(employee: Employee, period_start, period_end) -> dict:
    """Returns {'base_pay': Decimal, 'overtime_pay': Decimal, 'gross_pay': Decimal}
    for one employee over one pay period, based on their pay_type."""

    if employee.pay_type == "monthly":
        # Flat rate regardless of attendance, unless you want to prorate
        # for absences later — that logic would go here.
        base_pay = employee.monthly_rate or Decimal("0")
        overtime_pay = Decimal("0")

    elif employee.pay_type in ("daily", "hourly"):
        records = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= period_start,
            Attendance.date <= period_end,
        ).all()

        if employee.pay_type == "daily":
            days_present = sum(1 for r in records if r.status == "present")
            base_pay = (employee.daily_rate or Decimal("0")) * days_present
            overtime_hours = sum((r.overtime_hours or Decimal("0")) for r in records)
            hourly_equivalent = (employee.daily_rate or Decimal("0")) / Decimal("8")
            overtime_pay = hourly_equivalent * overtime_hours * Decimal("1.25")
        else:  # hourly
            total_hours = sum((r.hours_worked or Decimal("0")) for r in records)
            overtime_hours = sum((r.overtime_hours or Decimal("0")) for r in records)
            base_pay = (employee.hourly_rate or Decimal("0")) * total_hours
            overtime_pay = (employee.hourly_rate or Decimal("0")) * overtime_hours * Decimal("1.25")
    else:
        raise ValueError(f"Unknown pay_type '{employee.pay_type}' for {employee}")

    gross_pay = base_pay + overtime_pay
    return {"base_pay": base_pay, "overtime_pay": overtime_pay, "gross_pay": gross_pay}


def process_payroll_run(run):
    """Generates a Payslip for every active employee under this PayrollRun.
    Simple/manual deductions (cash advances, loans) should be attached to
    the employee BEFORE calling this — this function reads Deduction rows
    that already exist without a payslip_id... but since Deduction is
    currently modeled as payslip-scoped, wire up your manual-deduction UI
    to create Deduction rows right after each Payslip is created below."""

    employees = Employee.query.filter_by(status="active").all()

    for employee in employees:
        amounts = calculate_gross_pay(employee, run.period_start, run.period_end)

        payslip = Payslip(
            payroll_run_id=run.id,
            employee_id=employee.id,
            base_pay=amounts["base_pay"],
            overtime_pay=amounts["overtime_pay"],
            gross_pay=amounts["gross_pay"],
            total_deductions=Decimal("0"),
            net_pay=amounts["gross_pay"],
        )
        db.session.add(payslip)

    run.status = "processed"
    run.date_processed = datetime.utcnow()
    db.session.commit()


def recalculate_payslip_totals(payslip: Payslip):
    """Call after adding/removing Deduction rows on a payslip to keep
    total_deductions and net_pay in sync."""
    total = sum((d.amount for d in payslip.deductions), Decimal("0"))
    payslip.total_deductions = total
    payslip.net_pay = payslip.gross_pay - total
    db.session.commit()
