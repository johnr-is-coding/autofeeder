

class APIClientError(Exception):
    """Raised when a fatal API error occurs."""


class TransformerError(Exception):
    """Raised when a fatal error occurs during data transformation."""