from django.contrib import messages
from django.db.models import Q
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from grandchallenge.core.permissions.mixins import (
    UserAuthAndTestMixin,
    UserIsChallengeAdminMixin,
)
from grandchallenge.pages.forms import PageCreateForm, PageUpdateForm
from grandchallenge.pages.models import ErrorPage, Page
from grandchallenge.subdomains.utils import reverse


class ChallengeFilteredQuerysetMixin(object):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(Q(challenge=self.request.challenge))


class ChallengeFormKwargsMixin(object):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.request.challenge})
        return kwargs


class PageCreate(
    UserIsChallengeAdminMixin, ChallengeFormKwargsMixin, CreateView
):
    model = Page
    form_class = PageCreateForm

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)


class PageList(
    UserIsChallengeAdminMixin, ChallengeFilteredQuerysetMixin, ListView
):
    model = Page


class PageDetail(
    UserAuthAndTestMixin, ChallengeFilteredQuerysetMixin, DetailView
):
    model = Page
    slug_url_kwarg = "page_title"
    slug_field = "title__iexact"
    login_required = False

    def test_func(self):
        user = self.request.user
        page = self.get_object()
        return page.can_be_viewed_by(user=user)

    def get_context_object_name(self, obj):
        return "currentpage"


class ChallengeHome(PageDetail):
    def get_object(self, queryset=None):
        page = self.request.challenge.page_set.first()

        if page is None:
            page = ErrorPage(
                challenge=self.request.challenge,
                title="No Pages Found",
                html="No pages found for this site. Please log in and add some pages.",
            )

        return page


class PageUpdate(
    UserIsChallengeAdminMixin,
    ChallengeFilteredQuerysetMixin,
    ChallengeFormKwargsMixin,
    UpdateView,
):
    model = Page
    form_class = PageUpdateForm
    slug_url_kwarg = "page_title"
    slug_field = "title__iexact"
    template_name_suffix = "_form_update"

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.move(form.cleaned_data["move"])
        return response


class PageDelete(
    UserIsChallengeAdminMixin, ChallengeFilteredQuerysetMixin, DeleteView
):
    model = Page
    slug_url_kwarg = "page_title"
    slug_field = "title__iexact"
    success_message = "Page was successfully deleted"

    def get_success_url(self):
        return reverse(
            "pages:list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
