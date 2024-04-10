from django import template

register = template.Library()


@register.simple_tag
def csrf_data(request, csrf_token, csrf_header_name="X-CSRFToken"):
    if request:
        return {
            "csrfHeaderName": csrf_header_name,
            "csrfToken": str(csrf_token),
        }
    else:
        return ""
