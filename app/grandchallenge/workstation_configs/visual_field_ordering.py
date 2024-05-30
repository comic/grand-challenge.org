class Group:
    title: str
    description: str | None
    names: list[str]

    def __init__(self, *, title, description=None):
        self.title = title
        self.description = description
        self.names = []

    def add_to_group(self, other):
        self.names.append(other)


ABSOLUTE_FIELD_ORDER = [
    "title",
    "description",
    "image_context",
    "window_presets",
    "default_window_preset",
    "default_slab_thickness_mm",
    "default_slab_render_method",
    "default_orientation",
    "default_image_interpolation",
    "default_limit_view_area_to_image_volume",
    "key_bindings",
    "default_zoom_scale",
    Group(
        title="Annotations and Overlays",
        description="Behavior or visualization settings for annotations and overlays.",
    ),
    "overlay_luts",
    "default_overlay_lut",
    "default_overlay_alpha",
    "default_overlay_interpolation",
    "ghosting_slice_depth",
    "overlay_segments",
    "default_brush_size",
    "default_annotation_color",
    "default_annotation_line_width",
    "auto_jump_center_of_gravity",
    Group(
        title="Plugin and Tools",
        description="Plugins are components of the viewer, whereas tools are "
        "(generally) contained within plugins.",
    ),
    "show_image_info_plugin",
    "show_display_plugin",
    "show_image_switcher_plugin",
    "show_algorithm_output_plugin",
    "show_overlay_plugin",
    "show_annotation_statistics_plugin",
    "show_swivel_tool",
    "show_invert_tool",
    "show_flip_tool",
    "show_window_level_tool",
    "show_reset_tool",
    "show_overlay_selection_tool",
    "show_lut_selection_tool",
    "show_annotation_counter_tool",
    "enable_contrast_enhancement",
    Group(
        title="Linking Configuration",
        description="Linked images share tool interactions and display properties, "
        "it is possible to manually (un)link them during viewing.",
    ),
    "link_images",
    "link_panning",
    "link_zooming",
    "link_slicing",
    "link_orienting",
    "link_windowing",
    "link_inverting",
    "link_flipping",
]


def _construct_groups() -> list[Group]:
    current_group = Group(title="")

    i = 0
    while i < len(ABSOLUTE_FIELD_ORDER):
        if isinstance(ABSOLUTE_FIELD_ORDER[i], Group):
            yield current_group
            current_group = ABSOLUTE_FIELD_ORDER.pop(i)
        else:
            current_group.add_to_group(ABSOLUTE_FIELD_ORDER[i])
            i += 1

    yield current_group


GROUPS = tuple(_construct_groups())


FORM_FIELDS = list(ABSOLUTE_FIELD_ORDER)

DETAIL_FIELDS = list(ABSOLUTE_FIELD_ORDER)
DETAIL_FIELDS.remove("title")
DETAIL_FIELDS.remove("description")
