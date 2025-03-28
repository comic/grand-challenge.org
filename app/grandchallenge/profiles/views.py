from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.signing import BadSignature, Signer
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, UpdateView
from guardian.core import ObjectPermissionChecker
from guardian.mixins import LoginRequiredMixin
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.models import Job
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    UserPassesTestMixin,
    get_objects_for_user,
)
from grandchallenge.evaluation.models import Submission
from grandchallenge.organizations.models import Organization
from grandchallenge.profiles.forms import (
    NewsletterSignupForm,
    SubscriptionPreferenceForm,
    UserProfileForm,
)
from grandchallenge.profiles.models import (
    UNSUBSCRIBE_SALT,
    EmailSubscriptionTypes,
    NotificationEmailOptions,
    UserProfile,
)
from grandchallenge.profiles.serializers import UserProfileSerializer
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.tasks import update_verification_user_set


def profile(request):
    """Redirect to the profile page of the currently signed in user."""
    if request.user.is_authenticated:
        url = reverse(
            "profile-detail", kwargs={"username": request.user.username}
        )
    else:
        url = reverse("account_login")

    return redirect(url)


class UserProfileObjectMixin:
    def get_object(self, queryset=None):
        try:
            return (
                UserProfile.objects.select_related("user__verification")
                .exclude(user__username__iexact=settings.ANONYMOUS_USER_NAME)
                .get(user__username__iexact=self.kwargs["username"])
            )
        except ObjectDoesNotExist:
            raise Http404("User not found.")


class UserProfileDetail(UserProfileObjectMixin, DetailView):
    model = UserProfile
    context_object_name = "profile"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = context["object"].user
        profile_groups = profile_user.groups.all()

        organizations = Organization.objects.filter(
            Q(members_group__in=profile_groups)
            | Q(editors_group__in=profile_groups)
        ).distinct()

        archives = (
            get_objects_for_user(
                user=self.request.user,
                perms="archives.view_archive",
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(uploaders_group__in=profile_groups)
                | Q(users_group__in=profile_groups)
            )
            .distinct()
        )
        reader_studies = (
            get_objects_for_user(
                user=self.request.user,
                perms="reader_studies.view_readerstudy",
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(readers_group__in=profile_groups)
            )
            .distinct()
        )
        challenges = Challenge.objects.filter(
            Q(admins_group__in=profile_groups)
            | Q(participants_group__in=profile_groups),
            hidden=False,
        ).distinct()
        algorithms = (
            get_objects_for_user(
                user=self.request.user,
                perms="algorithms.view_algorithm",
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(users_group__in=profile_groups)
            )
            .distinct()
        )

        checker = ObjectPermissionChecker(user_or_group=profile_user)
        for qs in [archives, reader_studies, challenges, algorithms]:
            # Perms can only be prefetched for sets of the same objects
            checker.prefetch_perms(objects=qs)

        object_list = [*archives, *reader_studies, *challenges, *algorithms]

        role = {}
        for obj in object_list:
            obj_perms = checker.get_perms(obj)
            if f"change_{obj._meta.model_name}" in obj_perms:
                role[obj] = "editor"
            elif f"view_{obj._meta.model_name}" in obj_perms:
                role[obj] = "user"
            else:
                role[obj] = "participant"

        context.update(
            {
                "object_list": object_list,
                "object_role": role,
                "num_submissions": Submission.objects.filter(
                    creator=profile_user
                ).count(),
                "num_algorithms_run": Job.objects.filter(
                    creator=profile_user
                ).count(),
                "organizations": organizations,
            }
        )

        return context


class UserProfileUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = UserProfile
    form_class = UserProfileForm
    context_object_name = "profile"
    permission_required = "change_userprofile"
    raise_exception = True

    def get_object(self, queryset=None):
        try:
            return self.request.user.user_profile
        except ObjectDoesNotExist:
            raise Http404("User not found")


class NewsletterSignUp(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UserProfileObjectMixin,
    UpdateView,
):
    model = UserProfile
    form_class = NewsletterSignupForm
    context_object_name = "profile"
    permission_required = "change_userprofile"
    raise_exception = True

    def form_valid(self, form):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Newsletter preference successfully saved.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.GET.get("next")


class UserProfileViewSet(GenericViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ObjectPermissionsFilter,)
    queryset = UserProfile.objects.all()

    @action(detail=False, methods=["get"])
    def self(self, request):
        obj = get_object_or_404(UserProfile, user=request.user)
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data)


class EmailPreferencesUpdate(
    SuccessMessageMixin, UserPassesTestMixin, UpdateView
):
    model = UserProfile
    form_class = SubscriptionPreferenceForm
    template_name = "profiles/subscription_form.html"
    raise_exception = True
    subscription_type = None

    def test_func(self):
        try:
            username = self.username_from_token
        except BadSignature:
            return False

        try:
            user = get_user_model().objects.get(username=username)
        except ObjectDoesNotExist:
            return False

        if self.request.user.is_authenticated and user != self.request.user:
            update_verification_user_set.signature(
                kwargs={
                    "usernames": [
                        self.request.user.username,
                        user.username,
                    ]
                }
            ).apply_async()

        return super().test_func()

    @property
    def username_from_token(self):
        return Signer(salt=UNSUBSCRIBE_SALT).unsign_object(
            self.kwargs.get("token")
        )["username"]

    def get_object(self):
        return get_object_or_404(
            UserProfile, user__username=self.username_from_token
        )

    def get_success_url(self):
        return reverse(
            "email-preferences",
            kwargs={"token": self.kwargs.get("token")},
        )

    def get_success_message(self, cleaned_data):
        message = "You successfully updated your email preferences. "
        if self.subscription_type:
            message += f"You will no longer receive {self.subscription_type.lower()} emails."
        return message


class NewsletterUnsubscribeView(EmailPreferencesUpdate):
    subscription_type = EmailSubscriptionTypes.NEWSLETTER

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "receive_newsletter": False,
                "notification_email_choice": self.object.notification_email_choice,
                "autosubmit": True,
            }
        )
        return kwargs


class NotificationUnsubscribeView(EmailPreferencesUpdate):
    subscription_type = EmailSubscriptionTypes.NOTIFICATION

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "receive_newsletter": self.object.receive_newsletter,
                "notification_email_choice": NotificationEmailOptions.DISABLED,
                "autosubmit": True,
            }
        )
        return kwargs


class EmailPreferencesManagementView(EmailPreferencesUpdate):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "receive_newsletter": self.object.receive_newsletter,
                "notification_email_choice": self.object.notification_email_choice,
                "autosubmit": False,
            }
        )
        return kwargs
