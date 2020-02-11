from django import template
from django.templatetags.static import static

from grandchallenge.products.models import Product

register = template.Library()


@register.inclusion_tag("products/partials/navbar.html", takes_context=True)
def navbar(context):
    url = context.request.resolver_match.url_name
    return {
        "items": [
            {
                "url": "product_list",
                "active": url in ["product_list", "product_page"],
                "icon": "fa-th-large",
                "title": "Products",
            },
            {
                "url": "company_list",
                "active": url in ["company_list", "company_page"],
                "icon": "fa-th-large",
                "title": "Companies",
            },
            {
                "url": "about",
                "active": url == "about",
                "icon": "fa-user",
                "title": "About",
            },
            {
                "url": "contact",
                "active": url == "contact",
                "icon": "fa-envelope",
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
