"""
src/finder/shared/validation.py
------------------------------
Upload file validation helpers.
"""
import os
from werkzeug.datastructures import FileStorage
from finder.shared.errors import InvalidFileError, FileTooLargeError

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_resume_upload(file_obj: FileStorage):
    if not file_obj:
        raise InvalidFileError("No file was uploaded.")

    filename = file_obj.filename or ""
    if not filename:
        raise InvalidFileError("Uploaded file has no filename.")

    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileError(f"Unsupported file type: {ext}. Supported types: {', '.join(ALLOWED_EXTENSIONS)}")

    file_obj.stream.seek(0, os.SEEK_END)
    size = file_obj.stream.tell()
    file_obj.stream.seek(0)

    if size <= 0:
        raise InvalidFileError("Uploaded file is empty.")
    if size > MAX_FILE_SIZE:
        raise FileTooLargeError("Uploaded file exceeds the 10 MB size limit.")

    safe_name = os.path.basename(filename)
    return safe_name, ext, size
