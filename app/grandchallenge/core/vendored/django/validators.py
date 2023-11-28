import math

from django.core.validators import BaseValidator
from django.utils.translation import gettext_lazy as _


class StepValueValidator(BaseValidator):
    """StepValueValidator was introduced in django41 but corrected in django50 to include the offset.

    https://github.com/django/django/blob/21757bbdcd6ef31f2a4092fa1bd55dff29214c7a/django/core/validators.py#L396
    https://github.com/django/django/pull/16745

    """

    message = _(
        "Ensure this value is a multiple of step size %(limit_value)s."
    )
    code = "step_size"

    def __init__(self, limit_value, offset=None, message=None):
        super().__init__(limit_value, message)
        self.offset = 0 if offset is None else offset

    def compare(self, a, b):
        return not math.isclose(
            math.remainder(a - self.offset, b), 0, abs_tol=1e-9
        )
