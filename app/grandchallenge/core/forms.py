from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import CharField, ModelForm
from django.templatetags.static import static
from django.utils.html import format_html

from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.workstation_configs.models import WorkstationConfig
from grandchallenge.workstations.models import Workstation


class SaveFormInitMixin:
    """
    Mixin that adds some save features to a form via init:
      - a 'Save' button
      - disabling fieldsets after the form is submitted
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.attrs["gc-disable-after-submit"] = True
        self.helper.layout = Layout(
            Fieldset(
                None,  # Legend
                self.helper.layout,
            ),
            StrictButton(
                "Save",
                css_class="btn-primary",
                type="submit",
                css_id="submit-id-save",
            ),
        )

    class Media:
        js = [
            format_html(
                '<script type="module" src="{}"></script>',
                static("js/disable_after_submit.mjs"),
            )
        ]


class WorkstationUserFilterMixin:
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workstation"].queryset = filter_by_permission(
            queryset=Workstation.objects.order_by("title"),
            user=user,
            codename="view_workstation",
        )
        self.fields["workstation"].initial = Workstation.objects.get(
            slug=settings.DEFAULT_WORKSTATION_SLUG
        )

        self.fields["workstation_config"].queryset = (
            WorkstationConfig.objects.order_by("title")
        )


class UserFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class PermissionRequestUpdateForm(SaveFormInitMixin, ModelForm):
    """Update form for inheritors of RequestBase"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = (
            c
            for c in self.Meta.model.REGISTRATION_CHOICES
            if c[0] != self.Meta.model.PENDING
        )

    class Meta:
        fields = ("status", "rejection_text")


class UniqueTitleCreateFormMixin:
    """
    Form mixing creating an item with a unique title.

    Base class should have the `model` and `instance` attributes
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        field_order = list(self.field_order or self.fields.keys())
        self.fields["title"] = CharField(
            required=False,
            initial=self.instance and self.instance.title or "",
            max_length=self.model._meta.get_field("title").max_length,
        )
        self.order_fields(["title", *field_order])

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if title and self.unique_title_query(title).exists():
            raise ValidationError(
                f"There is already an existing {self.model._meta.verbose_name} with this title"
            )
        return title

    def unique_title_query(self, title):
        return self.model.objects.filter(title=title)


class UniqueTitleUpdateFormMixin(UniqueTitleCreateFormMixin):
    def unique_title_query(self, *args, **kwargs):
        return (
            super()
            .unique_title_query(*args, **kwargs)
            .exclude(id=self.instance.pk)
        )
