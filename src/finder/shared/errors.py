"""
src/finder/shared/errors.py
--------------------------
Custom exception types used across Finder services.
"""

class ResumeError(Exception):
    """Base class for resume-related errors."""
    def __init__(self, message: str, detail: str = None):
        super().__init__(message)
        self.detail = detail or message


class InvalidFileError(ResumeError):
    """Raised when the uploaded resume file is invalid or unsupported."""
    pass


class ParsingError(ResumeError):
    """Raised when resume parsing fails."""
    pass


class FileTooLargeError(ResumeError):
    """Raised when the uploaded file exceeds the allowed size."""
    pass
