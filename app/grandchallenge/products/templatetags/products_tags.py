from django import template
from django.template.defaultfilters import stringfilter
from django.templatetags.static import static

from grandchallenge.products.models import Product

register = template.Library()


@register.inclusion_tag("products/partials/navbar.html", takes_context=True)
def navbar(context):
    url = context.request.resolver_match.url_name
    return {
        "items": [
            {
                "url": "product-list",
                "active": url in ["product-list", "product-detail"],
                "title": "Products",
            },
            {
                "url": "company-list",
                "active": url in ["company-list", "company-detail"],
                "title": "Companies",
            },
            {
                "url": "project-air",
                "active": url == "project-air",
                "title": "Project AIR",
            },
            {
                "url": "blogs-list",
                "active": url == "blogs-list",
                "title": "Blogs",
            },
            {"url": "about", "active": url == "about", "title": "About"},
            {
                "url": "contact",
                "active": url == "contact",
                "title": "Contact",
            },
        ],
    }


@register.simple_tag
def icon(obj, field):
    value = getattr(obj, field, None)
    icon = Product.ICONS.get(value)
    if icon:
        return static(f"products/images/{icon}")


@register.filter
@stringfilter
def short(value, max_char):
    if len(value) > max_char:
        return value[:max_char].rsplit(" ", 1)[0] + " ..."
    return value
