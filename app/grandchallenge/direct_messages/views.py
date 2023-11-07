from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.direct_messages.forms import (
    ConversationForm,
    DirectMessageForm,
)
from grandchallenge.direct_messages.models import Conversation, DirectMessage


class ConversationCreate(LoginRequiredMixin, CreateView):
    # TODO permissions - check the user can create conversations and that they're able to contact this (set of users)
    # permission_required = "direct_messages.view_conversation"
    raise_exception = True
    model = Conversation
    form_class = ConversationForm

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)

        participants = get_user_model().objects.filter(
            username__in={self.request.user.username, self.kwargs["username"]}
        )

        form_kwargs.update({"participants": participants})

        return form_kwargs


class ConversationDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    permission_required = "direct_messages.view_conversation"
    raise_exception = True
    model = Conversation


class DirectMessageCreate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, CreateView
):
    permission_required = "direct_messages.create_conversation_direct_message"
    raise_exception = True
    model = DirectMessage
    form_class = DirectMessageForm

    @cached_property
    def conversation(self):
        return get_object_or_404(Conversation, pk=self.kwargs["pk"])

    def get_permission_object(self):
        return self.conversation

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs.update(
            {"sender": self.request.user, "conversation": self.conversation}
        )
        return form_kwargs
