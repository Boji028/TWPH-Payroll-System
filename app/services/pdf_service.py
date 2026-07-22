"""PDF generation for payslips, via WeasyPrint. Kept separate from
routes so both the admin and self-service download endpoints can reuse
it without duplicating the render-to-PDF logic.

WeasyPrint is imported inside the function, not at module load time.
It depends on native libraries (Pango) that pip alone can't install on
Windows — importing it at the top of this file would mean the entire
app fails to start (including `flask db upgrade`) if that native
dependency isn't set up yet, instead of only the PDF download routes
failing when actually used."""
from io import BytesIO
from flask import render_template


def render_payslip_pdf(payslip) -> bytes:
    """Renders one Payslip to PDF bytes using the print-only template —
    deliberately not base.html, since a PDF shouldn't include the site nav."""
    from weasyprint import HTML

    html = render_template("payroll/payslip_print.html", payslip=payslip)
    buffer = BytesIO()
    HTML(string=html).write_pdf(buffer)
    return buffer.getvalue()