from django.contrib import messages
from django.db.models import Q
from django.template import RequestContext, Template, TemplateSyntaxError
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    RedirectView,
    UpdateView,
)
from favicon.models import Favicon

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["currentpage"].html = render_tags(
            request=self.request, p=context["currentpage"]
        )
        return context


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


class FaviconView(RedirectView):
    """
    Some browsers do not follow the favicon links in base.html, so do this
    explicitly here.
    """

    permanent = False
    rel = "shortcut icon"

    def get_redirect_url(self, *args, **kwargs):
        fav = Favicon.objects.filter(isFavicon=True).first()

        if not fav:
            return None

        if self.rel == "shortcut icon":
            size = 32
        else:
            # This is the largest icon from
            # https://github.com/audreyr/favicon-cheat-sheet
            size = kwargs.get("size", 180)

        default_fav = fav.get_favicon(size=size, rel=self.rel)

        return default_fav.faviconImage.url


def render_tags(request, p, recursecount=0):
    """
    Render page contents using django template system

    This makes it possible to use tags like '{% dataset %}' in page content.
    If a rendered tag results in another tag, this can be rendered recursively
    as long as recurse limit is not exceeded.
    """
    recurselimit = 2
    try:
        t = Template("{% load grandchallenge_tags %}" + p.html)
    except TemplateSyntaxError as e:
        # when page contents cannot be rendered, just display raw contents and include error message on page
        errormsg = (
            '<span class="pageError"> Error rendering template: %s </span>' % e
        )
        pagecontents = p.html + errormsg
        return pagecontents

    # pass page to context here to be able to render tags based on which page does the rendering
    context = RequestContext(request, {"currentpage": p})
    pagecontents = t.render(context)

    if (
        "{%" in pagecontents or "{{" in pagecontents
    ):  # if rendered tags results in another tag, try to render this as well
        if recursecount < recurselimit:
            p2 = Page(title=p.title, challenge=p.challenge, html=pagecontents)
            return render_tags(request, p2, recursecount + 1)

        else:
            # when page contents cannot be rendered, just display raw contents and include error message on page
            errormsg = (
                '<span class="pageError"> Error rendering template: rendering recursed further than'
                + str(recurselimit)
                + " </span>"
            )
            pagecontents = p.html + errormsg
    return pagecontents
