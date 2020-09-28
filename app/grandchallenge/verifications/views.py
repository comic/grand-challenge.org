from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.timezone import now
from django.views.generic import CreateView, DetailView, FormView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.verifications.emails import send_verification_email
from grandchallenge.verifications.forms import (
    ConfirmEmailForm,
    VerificationForm,
)
from grandchallenge.verifications.models import Verification


class VerificationCreate(LoginRequiredMixin, CreateView):
    form_class = VerificationForm
    model = Verification

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form=form)

        if self.object.email.lower() != self.request.user.email.lower():
            send_verification_email(verification=self.object)
            messages.add_message(
                self.request,
                messages.INFO,
                f"Please check {self.object.email} for a confirmation link.",
            )

        return response


class VerificationDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Verification
    permission_required = "view_verification"
    raise_exception = True

    def get_object(self, queryset=None):
        try:
            return Verification.objects.get(
                user__username__iexact=self.kwargs["username"]
            )
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
        response = super().form_valid(form)

        self.request.user.verification.email_is_verified = True
        self.request.user.verification.email_verified_at = now()
        self.request.user.verification.save()

        messages.add_message(
            self.request,
            messages.INFO,
            "Your request is now under review by the site admins.",
        )

        return response

    def get_success_url(self):
        return self.request.user.verification.get_absolute_url()
