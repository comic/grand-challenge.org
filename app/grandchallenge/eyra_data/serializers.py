from rest_framework import serializers

from grandchallenge.eyra_data.models import DataFile, DataType


class DataTypeSerializer(serializers.ModelSerializer):
    # files = DataSetTypeFilesSerializer(many=True)
    class Meta:
        model = DataType
        fields = '__all__'


# class FileField(serializers.Field):
#     def to_representation(self, value):
#         if value._file:
#             return {
#                 'size': value.size,
#                 'url': value.url
#             }
#         else:
#             return {
#                 'size': 0,
#                 'url': ''
#             }
#

class DataFileSerializer(serializers.ModelSerializer):
    # file = FileField(read_only=True)
    class Meta:
        model = DataFile
        fields = '__all__'

    def update(self, instance, validated_data):
        if 'type' in validated_data:
            raise serializers.ValidationError({
                'type': 'Type cannot be changed.',
            })

        return super().update(instance, validated_data)
