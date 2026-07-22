"""PDF generation for payslips, via WeasyPrint. Kept separate from
routes so both the admin and self-service download endpoints can reuse
it without duplicating the render-to-PDF logic."""
from io import BytesIO
from flask import render_template
from weasyprint import HTML


def render_payslip_pdf(payslip) -> bytes:
    """Renders one Payslip to PDF bytes using the print-only template —
    deliberately not base.html, since a PDF shouldn't include the site nav."""
    html = render_template("payroll/payslip_print.html", payslip=payslip)
    buffer = BytesIO()
    HTML(string=html).write_pdf(buffer)
    return buffer.getvalue()
