from django.db.transaction import on_commit
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.fields import JSONField, ReadOnlyField, URLField
from rest_framework.relations import HyperlinkedRelatedField

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.archives.tasks import (
    start_archive_item_update_tasks,
    update_archive_item_update_kwargs,
)
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)
from grandchallenge.hanging_protocols.serializers import (
    HangingProtocolSerializer,
)


class ArchiveItemSerializer(serializers.ModelSerializer):
    archive = HyperlinkedRelatedField(
        read_only=True, view_name="api:archive-detail"
    )
    values = HyperlinkedComponentInterfaceValueSerializer(many=True)
    hanging_protocol = HangingProtocolSerializer(
        source="archive.hanging_protocol", read_only=True
    )
    view_content = JSONField(source="archive.view_content", read_only=True)

    class Meta:
        model = ArchiveItem
        fields = (
            "pk",
            "archive",
            "values",
            "hanging_protocol",
            "view_content",
        )


class ArchiveSerializer(serializers.ModelSerializer):
    algorithms = HyperlinkedRelatedField(
        read_only=True, many=True, view_name="api:algorithm-detail"
    )
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)
    # Include the read only name for legacy clients
    name = ReadOnlyField()

    class Meta:
        model = Archive
        fields = (
            "pk",
            "name",
            "title",
            "algorithms",
            "logo",
            "description",
            "api_url",
            "url",
        )


class ArchiveItemPostSerializer(ArchiveItemSerializer):
    archive = HyperlinkedRelatedField(
        queryset=Archive.objects.none(),
        view_name="api:archive-detail",
        write_only=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["values"] = ComponentInterfaceValuePostSerializer(
            many=True, context=self.context
        )

        if "request" in self.context:
            user = self.context["request"].user

            self.fields["archive"].queryset = get_objects_for_user(
                user, "archives.use_archive", accept_global_perms=False
            )

    def update(self, instance, validated_data):
        civs = validated_data.pop("values")

        all_civ_pks_to_remove = set()
        all_civ_pks_to_add = set()
        all_upload_pks = {}

        for civ in civs:
            interface = civ.pop("interface", None)
            upload_session = civ.pop("upload_session", None)
            value = civ.pop("value", None)
            image = civ.pop("image", None)
            user_upload = civ.pop("user_upload", None)

            (
                civ_pks_to_add,
                civ_pks_to_remove,
                upload_pks,
            ) = update_archive_item_update_kwargs(
                instance=instance,
                interface=interface,
                value=value,
                image=image,
                user_upload=user_upload,
                upload_session=upload_session,
            )
            all_civ_pks_to_add.update(civ_pks_to_add)
            all_civ_pks_to_remove.update(civ_pks_to_remove)
            all_upload_pks.update(upload_pks)

        on_commit(
            start_archive_item_update_tasks.signature(
                kwargs={
                    "archive_item_pk": instance.pk,
                    "civ_pks_to_add": list(civ_pks_to_add),
                    "civ_pks_to_remove": list(civ_pks_to_remove),
                    "upload_pks": upload_pks,
                }
            ).apply_async
        )

        return instance
