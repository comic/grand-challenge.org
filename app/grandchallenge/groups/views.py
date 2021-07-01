from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import CharField, Q, Value
from django.db.models.functions import Concat
from django.utils.html import format_html
from django.views.generic import FormView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.verifications.models import Verification


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


class UserAutocomplete(LoginRequiredMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = (
            get_user_model()
            .objects.order_by("username")
            .exclude(username=settings.ANONYMOUS_USER_NAME)
            .annotate(
                full_name=Concat(
                    "first_name",
                    Value(" "),
                    "last_name",
                    output_field=CharField(),
                )
            )
            .select_related("verification", "user_profile")
        )

        if self.q:
            qs = qs.filter(
                Q(username__icontains=self.q)
                | Q(email__icontains=self.q)
                | Q(full_name__icontains=self.q)
                | Q(verification__email__icontains=self.q)
            )

        return qs

    def get_result_label(self, result):

        try:
            is_verified = result.verification.is_verified
        except Verification.DoesNotExist:
            is_verified = False

        if is_verified:
            return format_html(
                '<img class="rounded-circle align-middle" src="{}" width ="20" height ="20"> '
                "&nbsp; <b>{}</b> &nbsp; {} &nbsp;"
                '<i class="fas fa-user-check text-success"></i>'
                "&nbsp;Verified email address at {}",
                result.user_profile.get_mugshot_url(),
                result.get_username(),
                result.get_full_name().title(),
                result.verification.email.split("@")[1],
            )
        else:
            return format_html(
                '<img class="rounded-circle align-middle" src="{}" width ="20" height ="20"> '
                "&nbsp; <b>{}</b> &nbsp; {}",
                result.user_profile.get_mugshot_url(),
                result.get_username(),
                result.get_full_name().title(),
            )
