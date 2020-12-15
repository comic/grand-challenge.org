from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.views.generic import DetailView, ListView
from guardian.mixins import LoginRequiredMixin
from guardian.shortcuts import get_objects_for_user

from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.groups.forms import EditorsForm, MembersForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.organizations.models import Organization


class OrganizationList(ListView):
    model = Organization
    ordering = "-created"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "jumbotron_title": "Organizations",
                "jumbotron_description": format_html(
                    (
                        "An organization is a group or institution who have "
                        "created an archive, reader study, challenge or "
                        "algorithm on this site. Please <a href='{}'>contact "
                        "us</a> if you would like to add your organization."
                    ),
                    random_encode("mailto:support@grand-challenge.org"),
                ),
            }
        )

        return context


class OrganizationDetail(DetailView):
    model = Organization


class OrganizationUserAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        return get_objects_for_user(
            user=self.request.user,
            perms="change_organization",
            klass=Organization,
        ).exists()

    def get_queryset(self):
        qs = (
            get_user_model()
            .objects.all()
            .order_by("username")
            .exclude(username=settings.ANONYMOUS_USER_NAME)
        )

        if self.q:
            qs = qs.filter(username__istartswith=self.q)

        return qs


class OrganizationUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "organizations/user_groups_form.html"
    permission_required = f"{Organization._meta.app_label}.change_{Organization._meta.model_name}"

    @property
    def obj(self):
        return get_object_or_404(Organization, slug=self.kwargs["slug"])


class OrganizationEditorsUpdate(OrganizationUserGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"


class OrganizationMembersUpdate(OrganizationUserGroupUpdateMixin):
    form_class = MembersForm
    success_message = "Members successfully updated"
