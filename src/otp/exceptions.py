class OTPException(Exception):
    """Base exception for all OTP violations."""
    def __int__(self,message: str):
        self.message = message
        super().__init__(message)

    
class InvalidOTPError(OTPException):
    """Raised when the submitted OTP code does not match the generated one."""
    def __init__(self, message: str = "The verification code provided is incorrect."):
        self.message = message
        super().__init__(message)

class ExpiredOTPError(OTPException):
    """Raised when an OTP code is valid but has surpassed its lifespan."""
    def __init__(self, message: str = "The verification code has expired. Please request a new one."):
        self.message = message
        super().__init__(message)

class OTPNotFoundError(OTPException):
    """Raised when no OTP is generated for a merchant."""
    def __init__(self, message: str = "No active OTP session found."):
        self.message = message
        super().__init__(message)

