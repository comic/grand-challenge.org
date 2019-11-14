from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ObjectDoesNotExist,
    ValidationError,
)
from django.db.models import Q
from django.forms.utils import ErrorList
from django.views.generic import CreateView, ListView, UpdateView

from grandchallenge.core.permissions.mixins import (
    UserIsChallengeAdminMixin,
    UserIsNotAnonMixin,
)
from grandchallenge.participants.emails import (
    send_participation_request_accepted_email,
    send_participation_request_notification_email,
    send_participation_request_rejected_email,
)
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.subdomains.utils import reverse


class ParticipantsList(UserIsChallengeAdminMixin, ListView):
    template_name = "participants/participants_list.html"

    def get_queryset(self):
        challenge = self.request.challenge
        return challenge.get_participants().select_related("user_profile")


class RegistrationRequestCreate(
    UserIsNotAnonMixin, SuccessMessageMixin, CreateView
):
    model = RegistrationRequest
    fields = ()

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
            if challenge.require_participant_review:
                # Note, sending an email here rather than in signals as
                # the function requires the request.
                send_participation_request_notification_email(
                    self.request, self.object
                )
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


class RegistrationRequestList(UserIsChallengeAdminMixin, ListView):
    model = RegistrationRequest

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(Q(challenge=self.request.challenge))
        return queryset


class RegistrationRequestUpdate(
    UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView
):
    model = RegistrationRequest
    fields = ("status",)
    success_message = "Registration successfully updated"

    def get_success_url(self):
        return reverse(
            "participants:registration-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )

    def form_valid(self, form):
        redirect = super().form_valid(form)
        # TODO: check if the status has actually changed
        if self.object.status == RegistrationRequest.ACCEPTED:
            send_participation_request_accepted_email(
                self.request, self.object
            )
        if self.object.status == RegistrationRequest.REJECTED:
            send_participation_request_rejected_email(
                self.request, self.object
            )
        return redirect
