

class APIClientError(Exception):
    """Raised when a fatal API error occurs."""


class ReportNotFoundError(APIClientError):
    """Raised when a report response is missing or invalid."""