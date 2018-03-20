from django.conf import settings
from django.core.exceptions import ValidationError


def validate_nounderscores(value):
    if "_" in value:
        raise ValidationError(
            u"underscores not allowed. The url \
            '{0}.{1}' would not be valid, "
            u"please use hyphens (-)".format(value, settings.MAIN_PROJECT_NAME)
        )