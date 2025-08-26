from django import template
from django.conf import settings

register = template.Library()


@register.filter
def euro(value):
    try:
        return f"€ {value:,.2f}"
    except ValueError:
        return ""


@register.filter
def euro_no_cents(value):
    try:
        return f"€ {value:,.0f}"
    except ValueError:
        return ""


@register.filter
def millicents_to_euro(millicents):
    try:
        return euro(millicents / 1000 / 100)
    except TypeError:
        return "-"


@register.filter
def storage_bytes_to_euro_per_year(storage_size):
    return millicents_to_euro(
        settings.COMPONENTS_S3_USD_MILLICENTS_PER_YEAR_PER_TB_EXCLUDING_TAX
        * (1 + settings.COMPONENTS_TAX_RATE)
        * settings.COMPONENTS_USD_TO_EUR
        * storage_size
        / settings.TERABYTE
    )


@register.filter
def registry_bytes_to_euro_per_year(storage_size):
    return millicents_to_euro(
        settings.COMPONENTS_ECR_USD_MILLICENTS_PER_YEAR_PER_TB
        * settings.COMPONENTS_USD_TO_EUR
        * storage_size
        / settings.TERABYTE
    )
