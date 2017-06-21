from rest_framework import serializers

from .models import Result


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ('user', 'challenge', 'method', 'metrics')
