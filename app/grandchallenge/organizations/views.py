from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.views.generic import DetailView, ListView, UpdateView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from guardian.shortcuts import get_objects_for_user

from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.groups.forms import EditorsForm, MembersForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.organizations.forms import OrganizationForm
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        editors_form = EditorsForm()
        editors_form.fields["action"].initial = EditorsForm.REMOVE

        members_form = MembersForm()
        members_form.fields["action"].initial = MembersForm.REMOVE

        context.update(
            {
                "editors_form": editors_form,
                "members_form": members_form,
                "object_list": self._organization_objects,
            }
        )

        return context

    @property
    def _organization_objects(self):
        algorithms = (
            get_objects_for_user(
                user=self.request.user,
                perms="algorithms.view_algorithm",
                accept_global_perms=False,
            )
            .filter(organizations__in=[self.object])
            .distinct()
        )
        archives = (
            get_objects_for_user(
                user=self.request.user,
                perms="archives.view_archive",
                accept_global_perms=False,
            )
            .filter(organizations__in=[self.object])
            .distinct()
        )
        challenges = (
            get_objects_for_user(
                user=self.request.user,
                perms="challenges.view_challenge",
                accept_global_perms=False,
            )
            .filter(organizations__in=[self.object])
            .distinct()
        )
        external_challenges = (
            get_objects_for_user(
                user=self.request.user,
                perms="challenges.view_externalchallenge",
                accept_global_perms=False,
            )
            .filter(organizations__in=[self.object])
            .distinct()
        )
        reader_studies = (
            get_objects_for_user(
                user=self.request.user,
                perms="reader_studies.view_readerstudy",
                accept_global_perms=False,
            )
            .filter(organizations__in=[self.object])
            .distinct()
        )

        object_list = [
            *archives,
            *reader_studies,
            *challenges,
            *external_challenges,
            *algorithms,
        ]

        return object_list


class OrganizationUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = Organization
    form_class = OrganizationForm
    permission_required = f"{Organization._meta.app_label}.change_{Organization._meta.model_name}"
    raise_exception = True


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
