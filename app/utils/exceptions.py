
class AutoFeederError(Exception):
    """Base exception for all application-specific errors."""


class APIClientError(AutoFeederError):
    """Raised when an API call fails or returns invalid data."""


class ReportNotFoundError(APIClientError):
    """Raised when a requested report cannot be found or has no usable detail payload."""


class TransformerError(AutoFeederError):
    """Raised when report transformation fails."""


class DatabaseError(AutoFeederError):
    """Raised when database operations fail."""


class ServiceError(AutoFeederError):
    """Raised when a service layer operation fails."""


class AppRuntimeError(AutoFeederError):
    """Raised when the application reaches an unrecoverable runtime state."""