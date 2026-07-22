from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.employee import Employee
from app.forms.employee_forms import EmployeeForm

employee_bp = Blueprint("employee", __name__)


@employee_bp.route("/")
@login_required
def list_employees():
    employees = Employee.query.order_by(Employee.last_name).all()
    return render_template("employees/list.html", employees=employees)


@employee_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee()
        form.populate_obj(employee)
        db.session.add(employee)
        db.session.commit()
        flash(f"Employee {employee.full_name} added.", "success")
        return redirect(url_for("employee.list_employees"))
    return render_template("employees/form.html", form=form, mode="create")


@employee_bp.route("/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    if form.validate_on_submit():
        form.populate_obj(employee)
        db.session.commit()
        flash(f"Employee {employee.full_name} updated.", "success")
        return redirect(url_for("employee.list_employees"))
    return render_template("employees/form.html", form=form, mode="edit", employee=employee)


@employee_bp.route("/<int:employee_id>/delete", methods=["POST"])
@login_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    employee.status = "inactive"  # soft delete — payroll history must stay intact
    db.session.commit()
    flash(f"Employee {employee.full_name} marked inactive.", "info")
    return redirect(url_for("employee.list_employees"))
