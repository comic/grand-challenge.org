from django.conf import settings

from grandchallenge.subdomains.utils import reverse


def signin_redirect(redirect=None, user=None):
    """
    Redirect user after successful sign in.
    First looks for a ``requested_redirect``. If not supplied will fall-back to
    the user specific account page. If all fails, will fall-back to redirect to
    the homepage. Returns a string defining the URI to go next.
    :param redirect:
        A value normally supplied by ``next`` form field. Gets preference
        before the default view which requires the user.
    :param user:
        A ``User`` object specifying the user who has just signed in.
    :return: String containing the URI to redirect to.
    """
    if redirect and settings.LOGOUT_URL not in redirect:
        return redirect
    elif user is not None and user.is_authenticated:
        return reverse("profile_redirect")
    else:
        return reverse("home")
