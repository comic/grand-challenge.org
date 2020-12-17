from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import FormView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from guardian.shortcuts import get_objects_for_user


class UserGroupUpdateMixin(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    raise_exception = True

    def get_permission_object(self):
        return self.obj

    @property
    def obj(self):
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.obj, "role": self.get_form().role})
        return context

    def get_success_url(self):
        return self.obj.get_absolute_url()

    def form_valid(self, form):
        form.add_or_remove_user(obj=self.obj)
        return super().form_valid(form)


class UserAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        allowed_perms = [
            "algorithms.change_algorithm",
            "organizations.change_organization",
        ]
        return any(
            get_objects_for_user(user=self.request.user, perms=perm,).exists()
            for perm in allowed_perms
        )

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
