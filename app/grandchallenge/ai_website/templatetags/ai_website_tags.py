from django import template
from django.templatetags.static import static

from grandchallenge.ai_website.models import ProductEntry

register = template.Library()


@register.simple_tag
def icon(obj, field):
    value = getattr(obj, field, None)
    icon = ProductEntry.ICONS.get(value)
    if icon:
        return static(f"ai_website/images/{icon}")
