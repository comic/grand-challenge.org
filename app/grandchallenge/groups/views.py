from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import FormView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)


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
