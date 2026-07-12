class TransactionException(Exception):
    """Based exception for Transactions violation"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class TransactionNotFoundError(TransactionException):
    """Raised when Transaction is not found"""
    def __init__(self, message:str="Transaction not found"):
        self.message = message
        super().__init__(self.message)