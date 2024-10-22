# Variable Reading
class VariableReadingException(Exception):
    def __init__(self, message):
        self.message = message

# Command Execution
class CommandExecutionException(Exception):
    def __init__(self, message):
        self.message = message

class WikiFormManagerException(Exception):
    def __init__(self, message):
        self.message = message

class SASPObjectValidationException(Exception):
    def __init__(self, message):
        self.message = message