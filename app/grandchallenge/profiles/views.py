from allauth_2fa.views import TwoFactorSetup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.views.generic import DetailView, FormView, TemplateView, UpdateView
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
    get_objects_for_user,
)
from grandchallenge.evaluation.models import Submission
from grandchallenge.organizations.models import Organization
from grandchallenge.profiles.forms import (
    NewsletterSignupForm,
    UnsubscribeForm,
    UserProfileForm,
)
from grandchallenge.profiles.models import SubscriptionTypes, UserProfile
from grandchallenge.profiles.serializers import UserProfileSerializer
from grandchallenge.subdomains.utils import reverse


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
    UserProfileObjectMixin,
    UpdateView,
):
    model = UserProfile
    form_class = UserProfileForm
    context_object_name = "profile"
    permission_required = "change_userprofile"
    raise_exception = True


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


class TwoFactorSetup(TwoFactorSetup):
    def form_invalid(self, form):
        response = super().form_invalid(form)
        # and display an error message
        messages.add_message(self.request, messages.ERROR, "Incorrect token.")
        return response


class OneClickUnsubscribeBaseView(SuccessMessageMixin, FormView):
    template_name = "profiles/unsubscribe.html"
    form_class = UnsubscribeForm
    subscription_type = None
    user_to_unsubscribe = None

    def get_success_message(self, cleaned_data):
        return (
            f"You successfully unsubscribed from "
            f"{self.subscription_type.value} emails."
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "token": self.kwargs.get("token"),
                "user": self.request.user,
            }
        )
        return kwargs

    def form_valid(self, form):
        self.user_to_unsubscribe = form.cleaned_data["user"]
        self.user_to_unsubscribe.user_profile.unsubscribe(
            subscription_type=self.subscription_type
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        super().form_invalid(form)
        return HttpResponseForbidden()

    def get_success_url(self):
        return reverse(
            "subscriptions",
            kwargs={"username": self.user_to_unsubscribe.username},
        )


class NewsletterUnsubscribeView(OneClickUnsubscribeBaseView):
    subscription_type = SubscriptionTypes.NEWSLETTER


class NotificationUnsubscribeView(OneClickUnsubscribeBaseView):
    subscription_type = SubscriptionTypes.NOTIFICATION


class SubscriptionView(TemplateView):
    template_name = "profiles/subscription_overview.html"

    @cached_property
    def user(self):
        return get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"current_user": self.user})
        return context
