# Add EmployeeDocument model

## What
Added `EmployeeDocument` model to support the HR Records feature — first step
in expanding the payroll system into a lightweight HRIS.

## Details
- New table `employee_documents`: doc_type, label, cloudinary_url,
  cloudinary_public_id, original_filename, expiry_date, notes,
  uploaded_by_id, uploaded_at
- FK to employees and users
- `is_expired` / `is_expiring_soon` helper properties for later dashboard use
- Migration: a5598d439e81_add_employee_documents_table.py

## Not yet done
Upload service, routes, templates