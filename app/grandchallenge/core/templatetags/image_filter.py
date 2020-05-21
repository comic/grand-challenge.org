from django import template

register = template.Library()


@register.simple_tag
def image_filter(alpha: float = 0.5) -> str:
    """A css image filter as a constant gradient."""
    return f"linear-gradient(to bottom, rgba(44,62,80,{alpha}) 0%, rgba(44,62,80,{alpha}) 100%)"
