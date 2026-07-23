# Fix missing requests dependency

## What
Added `requests` to requirements.txt — used directly in employee_routes.py
and self_service_routes.py to proxy-download documents from Cloudinary.
App failed to start without it.