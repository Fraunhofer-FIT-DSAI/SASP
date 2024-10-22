from .sasp_exceptions import WikiFormManagerException

class UnknownActionException(WikiFormManagerException):
    def __init__(self, message):
        super().__init__(message)