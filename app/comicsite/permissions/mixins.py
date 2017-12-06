from auth_mixins import UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden

from comicmodels.models import ComicSite
from comicsite.utils import build_absolute_uri


class UserAuthAndTestMixin(UserPassesTestMixin):
    """
    A mixin that is exactly like the UserPassesTest mixin, but ensures that
    the user is logged in too.

    Requires that comicsite.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """
    permission_denied_message = 'You do not have the correct permissions to access this page'

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated():
            messages.add_message(self.request, messages.INFO,
                                 'You need to login to access this page.')
            return redirect_to_login(build_absolute_uri(self.request),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())

        user_test_result = self.get_test_func()()

        if not user_test_result:
            return HttpResponseForbidden(self.get_permission_denied_message())

        return super(UserAuthAndTestMixin, self).dispatch(request, *args,
                                                          **kwargs)


class UserIsChallengeAdminMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is an admin for this challenge

    Requires that comicsite.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    def test_func(self):
        challenge = ComicSite.objects.get(short_name=self.request.projectname)
        return challenge.is_admin(self.request.user)


class UserIsChallengeParticipantOrAdminMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is a participant or an admin for this
    challenge

    Requires that comicsite.middleware.project is installed

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    def test_func(self):
        user = self.request.user
        challenge = ComicSite.objects.get(short_name=self.request.projectname)
        return challenge.is_admin(user) or challenge.is_participant(user)
