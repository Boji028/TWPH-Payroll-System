from flask_login import current_user
from app.models.employee_document import EmployeeDocument, DocumentType
from app.forms.document_forms import DocumentUploadForm
from app.services.document_service import upload_employee_document, delete_employee_document, DocumentUploadError
from flask import Blueprint, render_template, redirect, url_for, flash
from app.decorators import staff_required
from app.extensions import db
from app.models.employee import Employee
from app.models.user import User
from app.forms.employee_forms import EmployeeForm, EmployeeLoginForm
import requests
from io import BytesIO
from flask import send_file

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
@employee_bp.route("/<int:employee_id>/documents")
@staff_required
def list_documents(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    documents = employee.documents.order_by(EmployeeDocument.uploaded_at.desc()).all()
    form = DocumentUploadForm()
    return render_template("employees/documents.html", employee=employee, documents=documents, form=form)


@employee_bp.route("/<int:employee_id>/documents/upload", methods=["POST"])
@staff_required
def upload_document(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = DocumentUploadForm()

    if not form.validate_on_submit():
        flash("Please fix the errors and try again.", "danger")
        return redirect(url_for("employee.list_documents", employee_id=employee.id))

    try:
        upload_result = upload_employee_document(form.file.data, employee.id)
    except DocumentUploadError as e:
        flash(str(e), "danger")
        return redirect(url_for("employee.list_documents", employee_id=employee.id))

    document = EmployeeDocument(
        employee_id=employee.id,
        doc_type=DocumentType(form.doc_type.data),
        label=form.label.data,
        expiry_date=form.expiry_date.data,
        notes=form.notes.data,
        uploaded_by_id=current_user.id,
        **upload_result,
    )
    db.session.add(document)
    db.session.commit()
    flash(f"{document.label} uploaded.", "success")
    return redirect(url_for("employee.list_documents", employee_id=employee.id))


@employee_bp.route("/<int:employee_id>/documents/<int:document_id>/delete", methods=["POST"])
@staff_required
def delete_document(employee_id, document_id):
    document = EmployeeDocument.query.filter_by(id=document_id, employee_id=employee_id).first_or_404()
    delete_employee_document(document.cloudinary_public_id)
    db.session.delete(document)
    db.session.commit()
    flash(f"{document.label} deleted.", "info")
    return redirect(url_for("employee.list_documents", employee_id=employee_id))

@employee_bp.route("/<int:employee_id>/documents/<int:document_id>/download")
@staff_required
def download_document(employee_id, document_id):
    document = EmployeeDocument.query.filter_by(id=document_id, employee_id=employee_id).first_or_404()
    response = requests.get(document.cloudinary_url)
    response.raise_for_status()
    return send_file(
        BytesIO(response.content),
        mimetype=response.headers.get("Content-Type", "application/octet-stream"),
        as_attachment=True,
        download_name=document.original_filename,
    )