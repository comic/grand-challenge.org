from auth_mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

from comicmodels.models import ComicSite


class UserAuthAndTestMixin(UserPassesTestMixin):
    """
    A mixin that is exactly like the UserPassesTest mixin, but ensures that
    the user is logged in too.

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """
    permission_denied_message = 'You do not have the correct permissions to access this page'

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated():
            # Follow the default path, which is to login and try again
            return self.handle_no_permission()

        user_test_result = self.get_test_func()()

        if not user_test_result:
            raise PermissionDenied(self.get_permission_denied_message())

        return super(UserAuthAndTestMixin, self).dispatch(request, *args,
                                                          **kwargs)


class UserIsChallengeAdminMixin(UserAuthAndTestMixin):
    """
    A mixin that determines if a user is an admin for this challenge

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

    NOTE: YOU CANNOT INCLUDE MORE THAN ONE OF THESE MIXINS IN A CLASS!
    See https://docs.djangoproject.com/en/1.11/topics/auth/default/#django.contrib.auth.mixins.UserPassesTestMixin
    """

    def test_func(self):
        user = self.request.user
        challenge = ComicSite.objects.get(short_name=self.request.projectname)
        return challenge.is_admin(user) or challenge.is_participant(user)
