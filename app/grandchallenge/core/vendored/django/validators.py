import math

from django.core.validators import BaseValidator
from django.utils.translation import gettext_lazy as _


class StepValueValidator(BaseValidator):
    """
    Copied from Django 4.1:
    https://github.com/django/django/blob/21757bbdcd6ef31f2a4092fa1bd55dff29214c7a/django/core/validators.py#L396
    """

    message = _(
        "Ensure this value is a multiple of step size %(limit_value)s."
    )
    code = "step_size"

    def compare(self, a, b):
        return not math.isclose(math.remainder(a, b), 0, abs_tol=1e-9)
