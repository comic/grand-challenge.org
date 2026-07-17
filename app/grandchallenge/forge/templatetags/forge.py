from django import template

register = template.Library()


@register.filter
def has_json_kind(arg):
    return any(item.is_json_kind for item in arg)


@register.filter
def has_image_kind(arg):
    return any(item.is_image_kind for item in arg)


@register.filter
def has_panimg_kind(arg):
    return any(item.is_panimg_kind for item in arg)


@register.filter
def has_dicom_image_kind(arg):
    return any(item.is_dicom_image_kind for item in arg)


@register.filter
def is_string(arg):
    return isinstance(arg, str)


@register.filter
def has_file_kind(arg):
    return any(item.is_file_kind for item in arg)


@register.filter
def has_json_file_kind(arg):
    return any(item.is_json_file_kind for item in arg)


@register.filter(name="zip")
def zip_items(a, b):
    return zip(a, b, strict=True)


@register.filter
def dash_to_underscore(arg):
    return arg.replace("-", "_")
