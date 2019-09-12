from rest_framework import serializers

from comic.eyra_data.models import DataFile, DataType, DataSet


class DataTypeSerializer(serializers.ModelSerializer):
    # files = DataSetTypeFilesSerializer(many=True)
    class Meta:
        model = DataType
        fields = '__all__'


class FileField(serializers.FileField):
    def to_representation(self, value):
        if not getattr(value, 'url', None):
            return None
        return self.parent.instance.get_download_url()


class DataFileSerializer(serializers.ModelSerializer):
    file = FileField()

    class Meta:
        model = DataFile
        fields = '__all__'

    def update(self, instance, validated_data):
        if 'type' in validated_data:
            raise serializers.ValidationError({
                'type': 'Type cannot be changed.',
            })

        return super().update(instance, validated_data)


class DataSetSerializer(serializers.ModelSerializer):
    # files = DataSetTypeFilesSerializer(many=True)
    class Meta:
        model = DataSet
        fields = '__all__'
