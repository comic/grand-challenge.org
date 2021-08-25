from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db.models import Q
from django.forms.utils import ErrorList
from django.views.generic import CreateView, ListView, UpdateView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class ParticipantsList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, ListView
):
    template_name = "participants/participants_list.html"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_queryset(self):
        challenge = self.request.challenge
        return challenge.get_participants().select_related(
            "user_profile", "verification"
        )


class RegistrationRequestCreate(
    LoginRequiredMixin, SuccessMessageMixin, CreateView
):
    model = RegistrationRequest
    fields = ()
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        challenge = self.request.challenge
        return challenge.get_absolute_url()

    def get_success_message(self, cleaned_data):
        return self.object.status_to_string()

    def form_valid(self, form):
        challenge = self.request.challenge
        form.instance.user = self.request.user
        form.instance.challenge = challenge
        try:
            redirect = super().form_valid(form)
            return redirect

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            status = RegistrationRequest.objects.get(
                challenge=self.request.challenge, user=self.request.user
            ).status_to_string()
        except ObjectDoesNotExist:
            status = None
        context.update({"existing_status": status})
        return context


class RegistrationRequestList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, ListView
):
    model = RegistrationRequest
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(Q(challenge=self.request.challenge))
        return queryset


class RegistrationRequestUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = RegistrationRequest
    fields = ("status",)
    success_message = "Registration successfully updated"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_success_url(self):
        return reverse(
            "participants:registration-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )
