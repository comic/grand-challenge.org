from auth_mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS, \
    ObjectDoesNotExist
from django.db.models import Q
from django.forms.utils import ErrorList
from django.views.generic import ListView, CreateView, UpdateView

from comicmodels.models import RegistrationRequest, ComicSite
from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import UserIsChallengeAdminMixin
from participants.emails import (
    send_participation_request_notification_email,
    send_participation_request_accepted_email,
    send_participation_request_rejected_email,
)


class ParticipantsList(UserIsChallengeAdminMixin, ListView):
    def get_queryset(self):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.get_participants().select_related('user_profile')


class RegistrationRequestCreate(LoginRequiredMixin, SuccessMessageMixin,
                                CreateView):
    model = RegistrationRequest
    fields = ()

    def get_success_url(self):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.get_absolute_url()

    def get_success_message(self, cleaned_data):
        return self.object.status_to_string()

    def form_valid(self, form):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)

        form.instance.user = self.request.user
        form.instance.project = challenge

        try:
            redirect = super().form_valid(form)

            if challenge.require_participant_review:
                # Note, sending an email here rather than in signals as
                # the function requires the request.
                send_participation_request_notification_email(self.request,
                                                              self.object)

            return redirect
        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            status = RegistrationRequest.objects.get(
                project__pk=self.request.project_pk,
                user=self.request.user,
            ).status_to_string()
        except ObjectDoesNotExist:
            status = None

        context.update({'existing_status': status})

        return context


class RegistrationRequestList(UserIsChallengeAdminMixin, ListView):
    model = RegistrationRequest

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(Q(project__pk=self.request.project_pk))
        return queryset


class RegistrationRequestUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin,
                                UpdateView):
    model = RegistrationRequest
    fields = ('status',)
    success_message = 'Registration successfully updated'

    def get_success_url(self):
        return reverse(
            'participants:registration-list',
            kwargs={
                'challenge_short_name': self.object.project.short_name,
            }
        )

    def form_valid(self, form):
        redirect = super().form_valid(form)

        # TODO: check if the status has actually changed

        if self.object.status == RegistrationRequest.ACCEPTED:
            send_participation_request_accepted_email(self.request,
                                                      self.object)

        if self.object.status == RegistrationRequest.REJECTED:
            send_participation_request_rejected_email(self.request,
                                                      self.object)

        return redirect
