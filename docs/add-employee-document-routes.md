# Add employee document routes

## What
Added routes for uploading, listing, downloading, and deleting employee
documents — both the admin side and the employee self-service side.

## Details
- employee_routes.py: list_documents, upload_document, delete_document,
  download_document (all staff_required)
- self_service_routes.py: documents, download_document (both login_required,
  scoped to the current user's own employee record)
- Downloads are proxied through Flask (fetch from Cloudinary server-side,
  then send_file) rather than linking directly to the Cloudinary URL, so
  every download passes through an ownership check first

## Not yet done
Templates: employees/documents.html, self_service/documents.html