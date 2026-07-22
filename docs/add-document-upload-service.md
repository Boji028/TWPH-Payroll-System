# Add document upload service

## What
Added app/services/document_service.py — uploads employee documents to
Cloudinary. Uses a separate Cloudinary account from Travel Worthy PH to
isolate sensitive employee data.

## Details
- Validates file type (pdf, jpg, jpeg, png only) and size (max 10MB)
- Uploads with resource_type="auto", organized into
  employee_documents/<employee_id>/ folders
- Returns cloudinary_url, cloudinary_public_id, original_filename to save
  on EmployeeDocument
- delete_employee_document() removes a file from Cloudinary by public_id

## Note
Free-tier Cloudinary can block public PDF delivery by default — may need
a setting toggle if downloads get blocked later.

## Not yet done
Routes (upload/list/delete), templates