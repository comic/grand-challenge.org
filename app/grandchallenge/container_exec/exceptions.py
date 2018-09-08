class ContainerExecException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.message})"

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"

    def __eq__(self, other):
        return self.message == other.message

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.message)


class ExecContainerError(ContainerExecException):
    """ Raised when there is a problem with the executable container. """

    pass


class InputError(ContainerExecException):
    """ Raised when there is a problem with the input to a container. """

    pass
