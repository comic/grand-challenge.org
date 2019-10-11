from rest_framework.fields import CharField, FloatField
from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.workstation_configs.models import (
    WorkstationConfig,
    WindowPreset,
)


class WindowPresetSerializer(ModelSerializer):
    class Meta:
        model = WindowPreset
        fields = ["pk", "slug", "title", "description", "center", "width"]


class WorkstationConfigSerializer(ModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")
    default_slab_render_method = CharField(
        source="get_default_slab_render_method_display"
    )
    default_orientation = CharField(source="get_default_orientation_display")
    default_slab_thickness_mm = FloatField()
    window_presets = WindowPresetSerializer(many=True, read_only=True)
    default_window_preset = WindowPresetSerializer()

    class Meta:
        model = WorkstationConfig
        fields = [
            "pk",
            "slug",
            "title",
            "created",
            "modified",
            "creator",
            "window_presets",
            "default_window_preset",
            "default_slab_thickness_mm",
            "default_slab_render_method",
            "default_orientation",
        ]
