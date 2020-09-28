from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.views.generic import CreateView, DetailView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.verifications.forms import VerificationForm
from grandchallenge.verifications.models import Verification


class VerificationCreate(LoginRequiredMixin, CreateView):
    form_class = VerificationForm
    model = Verification

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


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
