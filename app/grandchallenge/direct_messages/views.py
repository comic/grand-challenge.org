from django.contrib.auth import get_user_model
from django.db.models import (
    BooleanField,
    Case,
    Count,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, ListView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    filter_by_permission,
)
from grandchallenge.direct_messages.forms import (
    ConversationForm,
    DirectMessageForm,
)
from grandchallenge.direct_messages.models import Conversation, DirectMessage
from grandchallenge.subdomains.utils import reverse


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


class ConversationList(LoginRequiredMixin, ListView):
    model = Conversation

    def get_queryset(self):
        queryset = super().get_queryset()

        most_recent_message = DirectMessage.objects.order_by("-created")

        queryset = (
            queryset.prefetch_related(
                "participants__user_profile",
                Prefetch(
                    "direct_messages",
                    queryset=most_recent_message.select_related("sender"),
                ),
            )
            .annotate(
                most_recent_message_created=Subquery(
                    most_recent_message.filter(
                        conversation=OuterRef("pk")
                    ).values("created")[:1]
                ),
                unread_message_count=Count(
                    "direct_messages",
                    filter=Q(direct_messages__unread_by=self.request.user),
                ),
                unread_by_user=Case(
                    When(unread_message_count=0, then=Value(False)),
                    default=Value(True),
                    output_field=BooleanField(),
                ),
            )
            .order_by("-unread_by_user", "-most_recent_message_created")
        )

        return filter_by_permission(
            queryset=queryset,
            user=self.request.user,
            codename="view_conversation",
        )


class ConversationDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    permission_required = "direct_messages.view_conversation"
    raise_exception = True
    model = Conversation

    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.prefetch_related(
            Prefetch(
                "direct_messages",
                queryset=DirectMessage.objects.order_by("created").annotate(
                    unread_by_user=Case(
                        When(unread_by=self.request.user, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField(),
                    )
                ),
            ),
            "direct_messages__sender__user_profile",
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        form = DirectMessageForm(
            sender=self.request.user, conversation=self.object
        )
        form.helper.attrs.update(
            {
                "hx-post": reverse(
                    "direct-messages:direct-message-create",
                    kwargs={"pk": self.object.pk},
                ),
                "hx-target": "#conversation-detail-panel",
            }
        )

        context.update({"form": form})
        return context


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
