# app/services/document_service.py
import os
from werkzeug.utils import secure_filename
import cloudinary.uploader

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE_MB = 10


class DocumentUploadError(Exception):
    """Raised when a document upload fails validation."""
    pass


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_employee_document(file_storage, employee_id):
    """
    Takes a file someone selected in a form, checks it's a valid
    type and size, uploads it to Cloudinary, and returns the info
    needed to save an EmployeeDocument record.
    """
    if not file_storage or file_storage.filename == "":
        raise DocumentUploadError("No file was selected.")

    filename = secure_filename(file_storage.filename)

    if not allowed_file(filename):
        raise DocumentUploadError("Only PDF, JPG, and PNG files are allowed.")

    file_storage.seek(0, os.SEEK_END)
    size_mb = file_storage.tell() / (1024 * 1024)
    file_storage.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        raise DocumentUploadError(f"File is too large (max {MAX_FILE_SIZE_MB}MB).")

    result = cloudinary.uploader.upload(
        file_storage,
        resource_type="auto",
        folder=f"employee_documents/{employee_id}",
        use_filename=True,
        unique_filename=True,
    )

    return {
        "cloudinary_url": result["secure_url"],
        "cloudinary_public_id": result["public_id"],
        "original_filename": filename,
    }


def delete_employee_document(cloudinary_public_id):
    """Removes a document from Cloudinary when it's deleted from the app."""
    cloudinary.uploader.destroy(cloudinary_public_id, resource_type="image")