from django import template
from django.contrib.auth.models import AbstractUser
from django.utils.html import format_html

from grandchallenge.subdomains.utils import reverse

register = template.Library()


@register.filter
def user_profile_link(user: AbstractUser) -> str:
    return format_html(
        (
            '<div style="vertical-align:middle; display:inline; white-space: nowrap;">'
            '  <a href="{0}">'
            '    <img class="mugshot" src="{1}" alt="User Mugshot" '
            '         style="height: 1.5em; vertical-align: middle;"/>'
            "    {2}"
            "  </a>"
            "</div>"
        ),
        reverse("userena_profile_detail", kwargs={"username": user.username}),
        user.user_profile.get_mugshot_url(),
        user.username,
    )
