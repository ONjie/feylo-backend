class MerchantException(Exception):
    """Base exception for all authentication violations."""
    def __init__(self, message: str):
     self.message = message
     super().__init__(self.message)


class MerchantNotFoundError(MerchantException):
   """Raised when Merchant is not Found"""
   def __init__(self, message: str="Merchant not found"):
      self.message = message
      super().__init__(self.message)


class MerchantNotVerifiedError(MerchantException):
   """Raised when Merchant is not verified"""
   def __init__(self, message: str="Merchant not verified"):
      self.message = message
      super().__init__(self.message)


class MerchantNotActiveError(MerchantException):
   """Raised when Merchant account is deactivated"""
   def __init__(self, message: str="Merchant account is currently deactivated"):
      self.message = message
      super().__init__(self.message)


class MerchantAlreadyExistError(MerchantException):
   """Raised when Merchant already exists"""
   def __init__(self, message: str="Merchant already exists"):
      self.message = message
      super().__init__(self.message)


class InvalidMerchantLookupError(MerchantException):
    """Raised when neither merchant_id nor phone_number is provided."""
    def __init__(self, message:str="Either merchant_id or phone_number must be provided."):
        self.message = message
        super().__init__(self.message)