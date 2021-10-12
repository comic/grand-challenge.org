from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.timezone import now
from django.views.generic import CreateView, DetailView, FormView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.emails import send_verification_email
from grandchallenge.verifications.forms import (
    ConfirmEmailForm,
    VerificationForm,
)
from grandchallenge.verifications.models import Verification


class VerificationRequiredMixin(UserPassesTestMixin):
    """Mixin for views that require verification"""

    def test_func(self):
        try:
            verified = self.request.user.verification.is_verified
        except ObjectDoesNotExist:
            verified = False

        if not verified:
            messages.error(
                self.request,
                "You need to verify your account before you can do this, "
                "you can request this from your profile page.",
            )

        return verified


class VerificationCreate(LoginRequiredMixin, CreateView):
    form_class = VerificationForm
    model = Verification

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form=form)

        if not self.object.signup_email_is_trusted:
            send_verification_email(verification=self.object)

        return response

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
