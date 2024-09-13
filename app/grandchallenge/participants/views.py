from collections import defaultdict
from typing import Any

from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    filter_by_permission,
)
from grandchallenge.participants.forms import (
    RegistrationQuestionCreateForm,
    RegistrationQuestionUpdateForm,
    RegistrationRequestForm,
)
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
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
    form_class = RegistrationRequestForm

    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        challenge = self.request.challenge
        return challenge.get_absolute_url()

    def get_success_message(self, cleaned_data):
        return self.object.status_to_string()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "challenge": self.request.challenge,
                "user": self.request.user,
            }
        )
        return kwargs

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
        queryset = queryset.filter(
            Q(challenge=self.request.challenge)
        ).select_related("user__user_profile", "user__verification")

        return queryset

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)

        questions = self._get_registration_questions()
        context_data["registration_questions"] = questions

        answers = self._get_registration_questions_answers(questions=questions)

        answer_lookup = defaultdict(dict)
        for answer in answers:
            answer_lookup[answer.registration_request.pk][
                answer.question.pk
            ] = answer

        context_data["registration_questions_answer_lookup"] = answer_lookup

        return context_data

    def _get_registration_questions(self):
        return filter_by_permission(
            queryset=self.request.challenge.registration_questions,
            user=self.request.user,
            codename="view_registrationquestion",
            accept_user_perms=False,
        )

    def _get_registration_questions_answers(self, questions):
        queryset = RegistrationQuestionAnswer.objects.filter(
            registration_request__in=self.object_list,
            question__in=questions,
        ).select_related("registration_request", "question")

        return filter_by_permission(
            queryset=queryset,
            user=self.request.user,
            codename="view_registrationquestionanswer",
            accept_user_perms=False,
        )


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

    def get_object(self, queryset=None):
        return get_object_or_404(
            self.model,
            challenge=self.request.challenge,
            pk=self.kwargs["pk"],
        )

    def get_permission_object(self):
        return self.request.challenge

    def get_success_url(self):
        return reverse(
            "participants:registration-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )


class RegistrationQuestionList(
    LoginRequiredMixin, PermissionListMixin, ListView
):
    model = RegistrationQuestion
    permission_required = "participants.view_registrationquestion"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(challenge=self.request.challenge)
        return queryset


class RegistrationQuestionCreate(
    LoginRequiredMixin,
    SuccessMessageMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = RegistrationQuestion
    form_class = RegistrationQuestionCreateForm
    permission_required = "challenges.add_registration_question"
    success_message = "Question successfully created"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["challenge"] = self.request.challenge
        return kwargs

    def get_success_url(self):
        return reverse(
            "participants:registration-question-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )


class RegistrationQuestionUpdate(
    LoginRequiredMixin,
    SuccessMessageMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = RegistrationQuestion
    form_class = RegistrationQuestionUpdateForm
    permission_required = "participants.change_registrationquestion"
    success_message = "Question successfully updated"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        return reverse(
            "participants:registration-question-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )


class RegistrationQuestionDelete(
    LoginRequiredMixin,
    SuccessMessageMixin,
    ObjectPermissionRequiredMixin,
    DeleteView,
):
    model = RegistrationQuestion
    permission_required = "participants.delete_registrationquestion"
    success_message = "Question successfully deleted"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        return reverse(
            "participants:registration-question-list",
            kwargs={"challenge_short_name": self.object.challenge.short_name},
        )
