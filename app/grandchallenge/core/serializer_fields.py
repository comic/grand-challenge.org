from rest_framework import serializers


class PkToHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    """
    A HyperlinkedRelatedField that allows you to use the primary key of the
    model when writing, but returns the URL of the object when reading.
    """

    def to_internal_value(self, data):
        return self.get_queryset().get(pk=data)
