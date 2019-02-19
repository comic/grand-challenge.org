from rest_framework import serializers

from grandchallenge.eyra_datasets.models import DataSet, DataSetType, DataSetTypeFile, DataSetFile


class DataSetTypeFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSetTypeFile
        fields = (
            "id",
            "required",
            "name",
        )
        depth = 1


class DataSetTypeSerializer(serializers.ModelSerializer):
    files = DataSetTypeFilesSerializer(many=True)

    class Meta:
        model = DataSetType
        fields = (
            "id",
            "created",
            "modified",
            "name",
            "files",
        )
        depth = 1


class FileField(serializers.Field):
    def to_representation(self, value):
        return {
            'size': value.size,
            'url': value.url
        }


class DataSetFileSerializer(serializers.ModelSerializer):
    file = FileField(read_only=True)
    class Meta:
        model = DataSetFile
        fields = (
            'id',
            'original_file_name',
            'file',
            'sha',
            'is_public',
            'dataset',
            'modified'
        )


class DataSetSerializer(serializers.ModelSerializer):
    files = DataSetFileSerializer(many=True, read_only=True)

    class Meta:
        model = DataSet
        fields = (
            "id",
            "created",
            "modified",
            "name",
            "type",
            "frozen",
            "files",
            "creator",
        )

    def update(self, instance, validated_data):
        if 'type' in validated_data:
            raise serializers.ValidationError({
                'type': 'Type cannot be changed.',
            })

        return super().update(instance, validated_data)
