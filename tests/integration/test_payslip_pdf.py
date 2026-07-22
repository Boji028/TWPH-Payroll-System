from datetime import date
from decimal import Decimal
import pytest
from app.extensions import db as _db
from app.models.user import User
from app.models.employee import Employee
from app.models.payroll import PayrollRun, Payslip
from app.models.deduction import Deduction

# WeasyPrint needs a native Pango install that isn't guaranteed to be set
# up on every machine (notably Windows without the MSYS2/Pango steps in
# docs/2026-07-22-payslip-pdfs.md). When that native library is missing,
# WeasyPrint raises a plain OSError from inside its own import (not an
# ImportError), so pytest.importorskip alone doesn't catch it — it would
# blow up test collection instead of just skipping. Catch both.
try:
    import weasyprint  # noqa: F401
except (ImportError, OSError) as exc:
    pytest.skip(f"WeasyPrint unavailable in this environment: {exc}", allow_module_level=True)


def _setup(db):
    owner = User(full_name="Owner Admin", email="owner@example.com", role="owner")
    owner.set_password("ownerpass1")
    emp = Employee(
        employee_code="EMP-001", first_name="Maria", last_name="Santos",
        pay_type="hourly", hourly_rate=Decimal("95"), date_hired=date(2025, 1, 1),
    )
    db.session.add_all([owner, emp])
    db.session.commit()

    run = PayrollRun(period_start=date(2026, 7, 1), period_end=date(2026, 7, 15), status="processed")
    db.session.add(run)
    db.session.commit()

    slip = Payslip(
        payroll_run_id=run.id, employee_id=emp.id,
        gross_pay=Decimal("9912.50"), total_deductions=Decimal("842"),
        net_pay=Decimal("9070.50"), base_pay=Decimal("9200"), overtime_pay=Decimal("712.50"),
    )
    db.session.add(slip)
    db.session.commit()
    db.session.add(Deduction(payslip_id=slip.id, type="cash_advance", description="Cash advance", amount=Decimal("842")))
    db.session.commit()
    return emp, slip


def login(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password})


def test_admin_can_download_payslip_pdf(db, client):
    emp, slip = _setup(db)
    login(client, "owner@example.com", "ownerpass1")
    r = client.get(f"/payroll/payslip/{slip.id}/pdf")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
    assert r.data[:4] == b"%PDF"


def test_pdf_reflects_actual_payslip_values(db, client):
    pytest.importorskip("pypdf", reason="pypdf needed to inspect PDF text content")
    from pypdf import PdfReader
    from io import BytesIO

    emp, slip = _setup(db)
    login(client, "owner@example.com", "ownerpass1")
    r = client.get(f"/payroll/payslip/{slip.id}/pdf")

    text = "".join(page.extract_text() for page in PdfReader(BytesIO(r.data)).pages)
    assert "Maria Santos" in text
    assert "9070.50" in text  # net pay
    assert "842.00" in text  # deduction
