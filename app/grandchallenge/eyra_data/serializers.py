from rest_framework import serializers

from grandchallenge.eyra_data.models import DataFile, DataType


class DataTypeSerializer(serializers.ModelSerializer):
    # files = DataSetTypeFilesSerializer(many=True)

    class Meta:
        model = DataType
        fields = (
            "id",
            "created",
            "modified",
            "name",
            # "files",
        )
        depth = 1


class FileField(serializers.Field):
    def to_representation(self, value):
        if value._file:
            return {
                'size': value.size,
                'url': value.url
            }
        else:
            return {
                'size': 0,
                'url': ''
            }


class DataSetSerializer(serializers.ModelSerializer):
    file = FileField(read_only=True)

    class Meta:
        model = DataFile
        fields = (
            "id",
            "created",
            "modified",
            "name",
            "type",
            "frozen",
            "file",
            "creator",
        )

    def update(self, instance, validated_data):
        if 'type' in validated_data:
            raise serializers.ValidationError({
                'type': 'Type cannot be changed.',
            })

        return super().update(instance, validated_data)
