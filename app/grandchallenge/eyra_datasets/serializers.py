from rest_framework import serializers

from grandchallenge.eyra_datasets.models import EyraDataSet


class EyraDataSetSerializer(serializers.HyperlinkedModelSerializer):
    creator = serializers.HyperlinkedRelatedField(
        view_name="api:user-detail", read_only=True
    )
    files = serializers.HyperlinkedRelatedField(
        view_name="api:datasetfile-detail", read_only=True
    )
    # participants_group = serializers.HyperlinkedRelatedField(
    #     view_name="api:group-detail", read_only=True
    # )
    # admins_group = serializers.HyperlinkedRelatedField(
    #     view_name="api:group-detail", read_only=True
    # )

    class Meta:
        model = EyraDataSet
        fields = (
            "pk",
            "created",
            "modified",
            "name",
            "type",
            "frozen",
            "files",
            # "use_evaluation",
            "creator",
            # "participants_group",
            # "admins_group",
        )


class EyraDataSetFileSerializer(serializers.HyperlinkedModelSerializer):
    dataset = serializers.HyperlinkedRelatedField(
        view_name="api:datasetfile", read_only=True
    )
    # participants_group = serializers.HyperlinkedRelatedField(
    #     view_name="api:group-detail", read_only=True
    # )
    # admins_group = serializers.HyperlinkedRelatedField(
    #     view_name="api:group-detail", read_only=True
    # )

    class Meta:
        model = EyraDataSet
        fields = (
            "pk",
            "created",
            "modified",
            "role",
            # "type",
            # "frozen",
            "file",
            # "use_evaluation",
            # "creator",
            # "participants_group",
            # "admins_group",
        )
