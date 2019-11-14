from django import template
from guardian.utils import get_anonymous_user
from rest_framework.authtoken.models import Token

register = template.Library()


@register.simple_tag
def auth_token(user):
    """Get the auth token for the user."""

    if user and user.pk != get_anonymous_user().pk:
        token, _ = Token.objects.get_or_create(user=user)
        return token
    else:
        return
