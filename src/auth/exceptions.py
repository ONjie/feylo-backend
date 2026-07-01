class AuthException(Exception):
    """Base exception for all authentication violations."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class InsufficientPermissionsError(AuthException):
    """Raised when a authenticated merchant attempts to access another merchant's record."""
    def __init__(self, message: str = "Not authorized to access this resource"):
        super().__init__(message)

class InvalidWebhookSignatureError(AuthException):
    """Raised when an incoming network provider callback fails HMAC verification."""
    def __init__(self, message: str = "Invalid provider webhook signature"):
        super().__init__(message)


class InvalidTokenError(AuthException):
    """Raised when the token is wrong or invalid"""

    def __init__(self, message: str ="Invalid token payload"):
        super().__init__(message)