from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.html import format_html
from django.utils.timezone import now
from django.views.generic import CreateView, DetailView, FormView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.evaluation.models import Submission
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.forms import (
    ConfirmEmailForm,
    VerificationForm,
)
from grandchallenge.verifications.models import (
    Verification,
    VerificationUserSet,
)


class VerificationRequiredMixin(AccessMixin):
    """Mixin for views that require verification"""

    def dispatch(self, request, *args, **kwargs):
        try:
            verified = request.user.verification.is_verified
        except ObjectDoesNotExist:
            verified = False

        if not verified:
            messages.error(
                request,
                format_html(
                    "You need to verify your account before you can do this, "
                    "you can request this <a href='{}'>on this page</a>.",
                    reverse("verifications:create"),
                ),
            )
            return self.handle_no_permission()
        else:
            return super().dispatch(request, *args, **kwargs)


class VerificationCreate(LoginRequiredMixin, CreateView):
    form_class = VerificationForm
    model = Verification

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse("verifications:detail")


class VerificationDetail(LoginRequiredMixin, DetailView):
    model = Verification

    def get_object(self, queryset=None):
        try:
            return self.request.user.verification
        except ObjectDoesNotExist:
            raise Http404("User not found")


class ConfirmEmailView(LoginRequiredMixin, FormView):
    form_class = ConfirmEmailForm
    template_name = "verifications/confirm_email_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"user": self.request.user, "token": self.kwargs["token"]}
        )
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form=form)

        self.request.user.verification.email_is_verified = True
        self.request.user.verification.email_verified_at = now()
        self.request.user.verification.save()

        return response

    def get_success_url(self):
        return reverse("verifications:detail")


class VerificationUserSetDetail(
    LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    model = VerificationUserSet
    permission_required = "verifications.view_verificationuserset"

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.prefetch_related(
            "users__verification", "users__user_profile"
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        domains = {
            user.verification.email.split("@")[1]
            for user in self.object.users.filter(
                verification__email_is_verified=True
            )
        }

        context.update(
            {
                "submissions": Submission.objects.filter(
                    creator__in=self.object.users.all()
                ).select_related(
                    "creator__verification",
                    "creator__user_profile",
                    "phase__challenge",
                ),
                "domains": domains,
            }
        )
        return context
