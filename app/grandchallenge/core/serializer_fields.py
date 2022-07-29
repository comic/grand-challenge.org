from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class PkToHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    """
    A HyperlinkedRelatedField that allows you to use the primary key of the
    model when writing, but returns the URL of the object when reading.
    """

    default_error_messages = {
        "required": _("This field is required."),
        "does_not_exist": _(
            'Invalid pk "{pk_value}" - object does not exist.'
        ),
        "incorrect_type": _(
            "Incorrect type. Expected pk value, received {data_type}."
        ),
    }

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(pk=data)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", pk_value=data)
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(data).__name__)
