class EvaluationException(Exception):
    pass


class TimeoutException(EvaluationException):
    """
    Raised when the evaluation of a submission takes too long. The challenge
    admin and site admin should be informed.
    """
    pass


class MethodContainerError(EvaluationException):
    """
    Raised when there is a problem with the method container. The challenge
    admin and site admin should be informed.
    """
    pass


class SubmissionError(EvaluationException):
    """
    Raised when there is a problem with the evaluation of a submission. The
    participant, challenge admin and site admin should be informed.
    """
    pass
