from allauth.mfa.utils import is_mfa_enabled
from django import template
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html

from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.subdomains.utils import reverse

register = template.Library()


@register.filter
def user_profile_link(user: AbstractUser | None) -> str:
    verified = ""

    if user:
        username = user.username
        profile_url = reverse(
            "profile-detail", kwargs={"username": user.username}
        )
        mugshot = format_html(
            (
                '<img class="rounded-circle border align-middle" loading="lazy" '
                'src="{0}" alt="User Mugshot" '
                # Match the "fa-lg" class style
                'style="height: 1.33em;"/>'
            ),
            user.user_profile.get_mugshot_url(),
        )

        try:
            verified = user.verification.verification_badge
        except ObjectDoesNotExist:
            # No verification request
            pass
    else:
        username = "Unknown"
        profile_url = "#"
        mugshot = clean('<i class="fas fa-user fa-lg"></i>')

    return format_html(
        '<span class="text-nowrap"><a href="{0}">{1}</a>&nbsp;<a href="{0}">{2}</a>&nbsp;{3}</span>',
        profile_url,
        mugshot,
        username,
        verified,
    )


@register.filter
def user_profile_link_username(username: str) -> str:
    return user_profile_links_from_usernames([username])[username]


@register.simple_tag
def user_profile_links_from_usernames(usernames):
    User = get_user_model()  # noqa: N806
    users = User.objects.filter(username__in=usernames).select_related(
        "user_profile", "verification"
    )
    return {user.username: user_profile_link(user) for user in users}


@register.filter
def has_2fa_enabled(user):
    return is_mfa_enabled(user)
