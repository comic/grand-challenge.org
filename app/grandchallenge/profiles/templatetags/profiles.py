from typing import NamedTuple

from allauth.mfa.utils import is_mfa_enabled
from django import template
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from grandchallenge.subdomains.utils import reverse

register = template.Library()


class UserProfileInformation(NamedTuple):
    profile_url: str
    mugshot: str
    verified: bool


def get_user_profile_details(user):
    verified = ""

    if user:
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
        profile_url = "#"
        mugshot = mark_safe('<i class="fas fa-user fa-lg"></i>')

    return UserProfileInformation(
        profile_url=profile_url,
        mugshot=mugshot,
        verified=verified,
    )


@register.filter
def user_profile_link(user: AbstractUser | None) -> str:
    user_details = get_user_profile_details(user)

    return format_html(
        '<span class="text-nowrap"><a href="{profile_url}">{mugshot}</a>&nbsp;<a href="{profile_url}">{username}</a>&nbsp;{verified}</span>',
        profile_url=user_details.profile_url,
        mugshot=user_details.mugshot,
        username=user.username,
        verified=user_details.verified,
    )


@register.filter
def user_profile_link_with_big_mugshot(user: AbstractUser | None) -> str:
    user_details = get_user_profile_details(user)

    return format_html(
        '<div><div class"embed-responsive embed-responsive-1by1 mb-1"><img class="card-img-top embed-responsive-item rounded-circle" src="{mugshot_url}" style="display: block; margin: auto;"/></div><div class="text-center"><b><a href="{profile_url}">{username}</a>&nbsp;{verified}</b></div></div>',
        profile_url=user_details.profile_url,
        mugshot_url=user.user_profile.get_mugshot_url(),
        username=user.username,
        verified=user_details.verified,
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
