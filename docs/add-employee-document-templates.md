# Add employee document templates

## What
Added the two templates for HR Records: admin document page and
employee self-service document page. Also fixed a bug found in the
routes from the previous session.

## Details
- employees/documents.html: upload form + document table (type, label,
  expiry with expired/expiring-soon flags, download, delete)
- self_service/documents.html: read-only document table for the
  logged-in employee
- Added "Documents" button to employees/list.html
- Added "My Documents" sidebar link to base.html
- Bug fix: employee_routes.py upload_document was passing a raw string
  for doc_type instead of a DocumentType enum instance, which would
  have failed at the database layer

## Not yet done
End-to-end testing of the full upload/download flow