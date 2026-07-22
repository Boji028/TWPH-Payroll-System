from flask import Blueprint, render_template, redirect, url_for, flash
from app.decorators import staff_required
from app.extensions import db
from app.models.employee import Employee
from app.models.user import User
from app.forms.employee_forms import EmployeeForm, EmployeeLoginForm

employee_bp = Blueprint("employee", __name__)


@employee_bp.route("/")
@staff_required
def list_employees():
    employees = Employee.query.order_by(Employee.last_name).all()
    return render_template("employees/list.html", employees=employees)


@employee_bp.route("/new", methods=["GET", "POST"])
@staff_required
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
@staff_required
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
@staff_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    employee.status = "inactive"  # soft delete — payroll history must stay intact
    db.session.commit()
    flash(f"Employee {employee.full_name} marked inactive.", "info")
    return redirect(url_for("employee.list_employees"))


@employee_bp.route("/<int:employee_id>/login", methods=["GET", "POST"])
@staff_required
def manage_login(employee_id):
    """Create or update the self-service login linked to this employee.
    No email invite is sent — share the password with the employee directly."""
    employee = Employee.query.get_or_404(employee_id)
    user = User.query.filter_by(employee_id=employee.id).first()
    form = EmployeeLoginForm(obj=user)

    if form.validate_on_submit():
        existing_email = User.query.filter(
            User.email == form.email.data, User.employee_id != employee.id
        ).first()
        if existing_email:
            flash("That email is already used by another login.", "danger")
            return render_template(
                "employees/create_login.html", form=form, employee=employee, user=user
            )

        if user is None and not form.password.data:
            flash("A password is required to create a new login.", "danger")
            return render_template(
                "employees/create_login.html", form=form, employee=employee, user=user
            )

        if user is None:
            user = User(
                full_name=employee.full_name,
                email=form.email.data,
                role="employee",
                employee_id=employee.id,
            )
        else:
            user.email = form.email.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()
        flash(f"Login saved for {employee.full_name}.", "success")
        return redirect(url_for("employee.list_employees"))

    return render_template("employees/create_login.html", form=form, employee=employee, user=user)