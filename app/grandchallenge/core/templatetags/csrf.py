from django import template

register = template.Library()


@register.simple_tag
def csrf_data(csrf_token, csrf_header_name="X-CSRFToken"):
    return {
        "csrfHeaderName": csrf_header_name,
        "csrfToken": str(csrf_token),
    }
