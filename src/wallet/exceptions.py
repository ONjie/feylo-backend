class WalletException(Exception):
    """Base exception for all wallet voilations"""
    def __init__(self, message: str):
     self.message = message
     super().__init__(self.message)


class WalletNotFoundError(WalletException):
   """Raised when wallet is not found based on the id provided"""
   def __init__(self, message: str = "Wallet Not Found"):
      self.message = message
      super().__init__(message)


class WalletAlreadyExistError(WalletException):
   """Raised when Wallet already exists"""
   def __init__(self, message: str="Wallet already exists"):
      self.message = message
      super().__init__(self.message)