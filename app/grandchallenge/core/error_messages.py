from enum import StrEnum


class SystemErrorMessages(StrEnum):
    UNEXPECTED_ERROR = "An unexpected error occurred"
    TIME_LIMIT_EXCEEDED = "Time limit exceeded"
    MEMORY_LIMIT_EXCEEDED = (
        "The container was killed as it exceeded its memory limit"
    )
