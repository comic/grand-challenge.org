from urllib.parse import urlparse, urlunparse

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect, QueryDict
from guardian.utils import get_anonymous_user

from grandchallenge.subdomains.utils import reverse


class UserAuthAndTestMixin(UserPassesTestMixin):
    """
    A mixin that is exactly like the UserPassesTest mixin, but ensures that
    the user is logged in if login_required is True.

    Requires that grandchallenge.core.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    login_required = True
    raise_exception = True

    def get_login_url(self):
        return reverse("userena_signin")

    def redirect_to_login(
        self, next, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME
    ):
        """
        Redirect the user to the login page, passing the given 'next' page.

        Uses the grand challenge reversal.
        """
        resolved_url = login_url or self.get_login_url()

        login_url_parts = list(urlparse(resolved_url))
        if redirect_field_name:
            querystring = QueryDict(login_url_parts[4], mutable=True)
            querystring[redirect_field_name] = next
            login_url_parts[4] = querystring.urlencode(safe="/")

        return HttpResponseRedirect(urlunparse(login_url_parts))

    def dispatch(self, request, *args, **kwargs):
        if self.login_required and not self.request.user.is_authenticated:
            messages.add_message(
                self.request,
                messages.INFO,
                "You need to login to access this page.",
            )
            return self.redirect_to_login(
                self.request.build_absolute_uri(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )

        return super().dispatch(request, *args, **kwargs)


class UserIsNotAnonMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is not anonymous. Like LoginRequiredMixin
    but works with subdomains

    DO NOT USE MORE THAN ONE OF THESE MIXINS
    """

    def test_func(self):
        return self.request.user != get_anonymous_user()


class UserIsChallengeAdminMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is an admin for this challenge

    Requires that grandchallenge.core.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    def test_func(self):
        challenge = self.request.challenge
        return challenge.is_admin(self.request.user)


class UserIsChallengeParticipantOrAdminMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is a participant or an admin for this
    challenge

    Requires that grandchallenge.core.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    def test_func(self):
        user = self.request.user
        challenge = self.request.challenge
        return challenge.is_admin(user) or challenge.is_participant(user)


class UserIsStaffMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is a staff member

    Requires that grandchallenge.core.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    def test_func(self):
        user = self.request.user
        return user.is_staff
