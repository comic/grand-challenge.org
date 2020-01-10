from django.forms import ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.workstation_configs.models import WorkstationConfig


class WorkstationConfigForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = WorkstationConfig
        fields = (
            "title",
            "description",
            "window_presets",
            "default_window_preset",
            "default_slab_thickness_mm",
            "default_slab_render_method",
            "default_orientation",
            "default_overlay_alpha",
            "default_overlay_lut",
            "default_overlay_interpolation",
            "default_zoom_scale",
            "show_image_info_plugin",
            "show_display_plugin",
        )
