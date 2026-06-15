from enum import StrEnum


class LambdaTaskQueueChoices(StrEnum):
    DEFAULT = "default"
    MEM8G = "mem8g"
    BATCH_MEM8G = "batch-mem8g"


LONG_TASK_SOFT_TIMEOUT = 14 * 60
LONG_TASK_HARD_TIMEOUT = LONG_TASK_SOFT_TIMEOUT + 30
