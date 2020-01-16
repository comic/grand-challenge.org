from django import template

from grandchallenge.subdomains.utils import reverse

register = template.Library()


@register.simple_tag()
def url(view_name, *args, **kwargs):
    return reverse(view_name, args=args, kwargs=kwargs)
