from django.contrib.auth import get_user_model
from django.views.generic import CreateView, DetailView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.direct_messages.forms import ConversationForm
from grandchallenge.direct_messages.models import Conversation


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


class ConversationDetail(ObjectPermissionRequiredMixin, DetailView):
    permission_required = "direct_messages.view_conversation"
    raise_exception = True
    model = Conversation
