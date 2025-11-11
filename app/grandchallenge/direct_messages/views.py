from dateutil.utils import today
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from guardian.mixins import LoginRequiredMixin

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
)
from grandchallenge.direct_messages.forms import (
    ConversationForm,
    DirectMessageForm,
    DirectMessageReportSpamForm,
    MuteDeleteForm,
    MuteForm,
)
from grandchallenge.direct_messages.models import (
    Conversation,
    DirectMessage,
    DirectMessageUnreadBy,
    Mute,
)
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


class ConversationCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    raise_exception = True
    model = Conversation
    form_class = ConversationForm

    def test_func(self):
        if settings.ANONYMOUS_USER_NAME == self.kwargs["username"]:
            return False
        else:
            # Only challenge or reader study admins can message their participants
            return (
                Challenge.objects.filter(
                    admins_group__user=self.request.user,
                    participants_group__user__username=self.kwargs["username"],
                    is_active_until__gt=today().date(),
                ).exists()
                or ReaderStudy.objects.filter(
                    editors_group__user=self.request.user,
                    readers_group__user__username=self.kwargs["username"],
                ).exists()
            )

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)

        participants = get_user_model().objects.filter(
            username__in={self.request.user.username, self.kwargs["username"]}
        )

        form_kwargs.update({"participants": participants})

        return form_kwargs

    def form_invalid(self, form):
        if form.has_error(field="participants", code="CONVERSATION_EXISTS"):
            return redirect(to=form.existing_conversations.get().list_view_url)
        else:
            return super().form_invalid(form)

    def get_success_url(self):
        return self.object.list_view_url


class MutedUsersMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        context.update(
            {
                "muted_usernames": {
                    *Mute.objects.filter(source=self.request.user).values_list(
                        "target__username", flat=True
                    )
                },
            }
        )

        return context


class ConversationList(
    LoginRequiredMixin,
    MutedUsersMixin,
    ViewObjectPermissionListMixin,
    ListView,
):
    model = Conversation

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(participants=self.request.user)
            .with_most_recent_message(user=self.request.user)
            .order_by("-unread_by_user", "-most_recent_message_created")
        )


class ConversationDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    MutedUsersMixin,
    DetailView,
):
    permission_required = "direct_messages.view_conversation"
    raise_exception = True
    model = Conversation

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.with_unread_by_user(
            user=self.request.user
        ).prefetch_related("direct_messages__sender__user_profile")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        direct_message_form = DirectMessageForm(
            sender=self.request.user, conversation=self.object
        )
        direct_message_form.helper.attrs.update(
            {
                "hx-post": reverse(
                    "direct-messages:direct-message-create",
                    kwargs={"pk": self.object.pk},
                ),
                "hx-target": "#conversation-detail-panel",
            }
        )

        context.update(
            {
                "direct_message_form": direct_message_form,
                "report_spam_form": DirectMessageReportSpamForm(),
            }
        )
        return context


class ConversationSelectDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    MutedUsersMixin,
    DetailView,
):
    permission_required = "direct_messages.view_conversation"
    raise_exception = True
    model = Conversation
    template_name = "direct_messages/partials/conversation_select_detail.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.with_most_recent_message(user=self.request.user)


class ConversationMarkRead(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    permission_required = "direct_messages.mark_conversation_read"
    raise_exception = True
    model = Conversation
    fields = ()

    def form_valid(self, form):
        DirectMessageUnreadBy.objects.filter(
            direct_message__conversation=self.object,
            unread_by=self.request.user,
        ).delete()
        return super().form_valid(form)


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


class DirectMessageReportSpam(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    permission_required = "direct_messages.mark_conversation_message_as_spam"
    raise_exception = True
    model = DirectMessage
    form_class = DirectMessageReportSpamForm

    def get_object(self, *args, **kwargs):
        return get_object_or_404(
            DirectMessage,
            pk=self.kwargs["pk"],
            conversation__pk=self.kwargs["conversation_pk"],
        )

    @cached_property
    def conversation(self):
        return self.get_object().conversation

    def get_permission_object(self):
        return self.conversation

    def get_success_url(self):
        return reverse(
            "direct-messages:conversation-detail",
            kwargs={"pk": self.conversation.pk},
        )


class DirectMessageDelete(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView
):
    permission_required = "direct_messages.delete_directmessage"
    raise_exception = True
    model = DirectMessage

    def get_object(self, *args, **kwargs):
        return get_object_or_404(
            DirectMessage,
            pk=self.kwargs["pk"],
            conversation__pk=self.kwargs["conversation_pk"],
        )

    def get_success_url(self):
        return reverse(
            "direct-messages:conversation-detail",
            kwargs={"pk": self.object.conversation.pk},
        )


class MuteCreate(LoginRequiredMixin, CreateView):
    model = Mute
    form_class = MuteForm

    @property
    def target(self):
        return get_object_or_404(
            get_user_model(), username=self.kwargs["username"]
        )

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)

        form_kwargs.update(
            {"source": self.request.user, "target": self.target}
        )

        return form_kwargs

    def form_valid(self, form):
        self.success_url = form.cleaned_data["conversation"].get_absolute_url()
        return super().form_valid(form)


class MuteDelete(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView
):
    permission_required = "direct_messages.delete_mute"
    raise_exception = True
    model = Mute
    form_class = MuteDeleteForm

    def get_object(self, *args, **kwargs):
        return get_object_or_404(
            Mute,
            source=self.request.user,
            target__username=self.kwargs["username"],
        )

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)

        form_kwargs.update({"user": self.request.user})

        return form_kwargs

    def form_valid(self, form):
        self.success_url = form.cleaned_data["conversation"].get_absolute_url()
        return super().form_valid(form)
