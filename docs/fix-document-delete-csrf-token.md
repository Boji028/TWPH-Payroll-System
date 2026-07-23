# Fix missing CSRF token on document delete form

## What
Fixed the delete button on employees/documents.html — the delete form
was plain HTML (not WTForms-rendered), so it had no CSRF token and
failed with a 400 Bad Request. Same bug class as the earlier missing
tokens on attendance/payroll forms.

## Details
Added a hidden csrf_token input to the delete form in
employees/documents.html.