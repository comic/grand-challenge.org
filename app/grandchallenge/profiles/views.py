from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView
from django.views.generic.edit import FormView
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import get_objects_for_user
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from userena import views as userena_views

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyPermissions,
)
from grandchallenge.evaluation.models import Submission
from grandchallenge.profiles.filters import UserProfileObjectPermissionsFilter
from grandchallenge.profiles.forms import EditProfileForm, PreSocialForm
from grandchallenge.profiles.models import UserProfile
from grandchallenge.profiles.serializers import UserProfileSerializer
from grandchallenge.profiles.utils import signin_redirect
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


def login_redirect(request):
    next_uri = request.GET.get("next")
    redirect_uri = signin_redirect(redirect=next_uri, user=request.user)
    return redirect(redirect_uri)


def profile(request):
    """Redirect to the profile page of the currently signed in user."""
    if request.user.is_authenticated:
        url = reverse(
            "userena_profile_detail",
            kwargs={"username": request.user.username},
        )
    else:
        url = reverse("profile_signin")

    return redirect(url)


def profile_edit_redirect(request):
    """Redirect to the profile edit page of the currently signed in user."""
    if request.user.is_authenticated:
        messages.add_message(
            request,
            messages.INFO,
            "Please fill-in the missing information in the form form below.",
        )
        url = reverse(
            "userena_profile_edit", kwargs={"username": request.user.username}
        )
    else:
        url = reverse("profile_signin")

    return redirect(url)


def profile_edit(*args, **kwargs):
    kwargs["edit_profile_form"] = EditProfileForm
    return userena_views.profile_edit(*args, **kwargs)


def signup(request, extra_context=None, **kwargs):
    success = reverse("profile_signup_complete")
    response = userena_views.signup(
        request=request,
        extra_context=extra_context,
        success_url=success,
        **kwargs,
    )
    return response


def signin(request, **kwargs):
    redirect_signin_function = signin_redirect
    response = userena_views.signin(
        request=request,
        redirect_signin_function=redirect_signin_function,
        **kwargs,
    )
    return response


def signup_complete(request):
    response = render(request, "userena/signup_complete.html")
    return response


class UserProfileDetail(UserPassesTestMixin, DetailView):
    template_name = "userena/profile_detail.html"
    context_object_name = "profile"

    def get_test_func(self):
        profile = self.get_object()

        def can_view_profile():
            return profile.can_view_profile(self.request.user)

        return can_view_profile

    def get_object(self, queryset=None):
        try:
            return UserProfile.objects.select_related(
                "user__verification"
            ).get(user__username__iexact=self.kwargs["username"])
        except ObjectDoesNotExist:
            raise Http404("User not found.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile_user = context["object"].user
        profile_groups = profile_user.groups.all()

        archives = (
            get_objects_for_user(
                user=self.request.user,
                perms="view_archive",
                klass=Archive,
                use_groups=True,
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
                perms="view_readerstudy",
                klass=ReaderStudy,
                use_groups=True,
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
                perms="view_algorithm",
                klass=Algorithm,
                use_groups=True,
            )
            .filter(
                Q(editors_group__in=profile_groups)
                | Q(users_group__in=profile_groups)
            )
            .distinct()
        )

        checker = ObjectPermissionChecker(user_or_group=profile_user)
        for qs in [
            archives,
            reader_studies,
            challenges,
            algorithms,
        ]:
            # Perms can only be prefetched for sets of the same objects
            checker.prefetch_perms(objects=qs)

        object_list = [
            *archives,
            *reader_studies,
            *challenges,
            *algorithms,
        ]

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
            }
        )

        return context


class PreSocialView(FormView):
    form_class = PreSocialForm
    template_name = "profiles/pre_social_form.html"

    def get_success_url(self, *args, **kwargs):
        return reverse("social:begin", args=["google-oauth2"])


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = (DjangoObjectOnlyPermissions,)
    filter_backends = (UserProfileObjectPermissionsFilter,)
    queryset = UserProfile.objects.all()

    @action(detail=False, methods=["get"])
    def self(self, request):
        obj = get_object_or_404(UserProfile, user=request.user)
        if not request.user.has_perm("view_profile", obj):
            raise PermissionDenied()
        serializer = self.get_serializer(instance=obj)
        return Response(serializer.data)
