from enum import StrEnum


class SystemErrorMessages(StrEnum):
    UNEXPECTED_ERROR = "An unexpected error occurred"
    TIME_LIMIT_EXCEEDED = "Time limit exceeded"
    MEMORY_LIMIT_EXCEEDED = (
        "The container was killed as it exceeded its memory limit"
    )


class EvaluationErrorMessages(StrEnum):
    ALGORITHM_FAILURE = "The algorithm failed on one or more cases."
    UNSUCCESSFUL_JOBS = "There are non-successful jobs for this submission."
    INTERFACE_MISMATCH = (
        "The algorithm interfaces do not match those defined for the phase."
    )
    UNSUPPORTED_INPUT = "Input file type is not supported"
