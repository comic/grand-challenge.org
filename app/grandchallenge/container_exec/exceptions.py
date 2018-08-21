class ContainerExecException(Exception):
    def __init__(self, message):
        self.message = message
        super(ContainerExecException, self).__init__()


class ExecContainerError(ContainerExecException):
    """ Raised when there is a problem with the executable container. """

    pass


class InputError(ContainerExecException):
    """ Raised when there is a problem with the input to a container. """

    pass
