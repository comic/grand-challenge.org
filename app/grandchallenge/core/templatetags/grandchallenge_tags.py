from grandchallenge.core.templatetags import library_plus
from grandchallenge.subdomains.utils import reverse

register = library_plus.LibraryPlus()


@register.simple_tag()
def url(view_name, *args, **kwargs):
    return reverse(view_name, args=args, kwargs=kwargs)
