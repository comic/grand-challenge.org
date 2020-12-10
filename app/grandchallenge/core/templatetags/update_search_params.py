from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def update_search_params(context, **kwargs):
    """Update the set parameters of the current request"""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()
