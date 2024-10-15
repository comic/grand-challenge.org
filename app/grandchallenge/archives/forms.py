from dal import autocomplete
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Exists, OuterRef
from django.forms import (
    Form,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    TextInput,
)
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.archives.models import (
    Archive,
    ArchiveItem,
    ArchivePermissionRequest,
)
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.components.forms import (
    CIVSetCreateFormMixin,
    CIVSetUpdateFormMixin,
    MultipleCIVForm,
)
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    UniqueTitleCreateFormMixin,
    UniqueTitleUpdateFormMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.widgets import (
    JSONEditorWidget,
    MarkdownEditorInlineWidget,
)
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.models import VIEW_CONTENT_SCHEMA
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse_lazy


class ArchiveForm(
    WorkstationUserFilterMixin,
    SaveFormInitMixin,
    ModelForm,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].required = True
        self.fields["workstation"].required = True
        active_image_subquery = AlgorithmImage.objects.filter(
            algorithm=OuterRef("pk"), is_desired_version=True
        )
        self.fields["algorithms"].queryset = (
            (
                self.instance.algorithms.all()
                | get_objects_for_user(
                    kwargs["user"],
                    "algorithms.execute_algorithm",
                )
            )
            .annotate(has_active_image=Exists(active_image_subquery))
            .filter(has_active_image=True)
            .distinct()
        )
        if self.instance:
            interface_slugs = (
                self.instance.items.exclude(values__isnull=True)
                .values_list("values__interface__slug", flat=True)
                .order_by()
                .distinct()
            )
            self.fields["view_content"].help_text += (
                " The following interfaces are used in your archive: "
                f"{', '.join(interface_slugs)}."
            )

    class Meta:
        model = Archive
        fields = (
            "title",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "logo",
            "social_image",
            "workstation",
            "workstation_config",
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
            "algorithms",
            "public",
            "access_request_handling",
            "detail_page_markdown",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorInlineWidget,
            "algorithms": Select2MultipleWidget,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
            "optional_hanging_protocols": Select2MultipleWidget,
            "view_content": JSONEditorWidget(schema=VIEW_CONTENT_SCHEMA),
        }
        help_texts = {
            "workstation_config": format_lazy(
                (
                    "The viewer configuration to use for this archive. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'configurations, go <a href="{}">here</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
                reverse_lazy("workstation-configs:list"),
            ),
            "publications": format_lazy(
                (
                    "The publications associated with this archive. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            ),
            "hanging_protocol": format_lazy(
                (
                    "The hanging protocol to use for this archive. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
            "optional_hanging_protocols": format_lazy(
                (
                    "Other hanging protocols that can be used for this algorithm. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
            "algorithms": "Select algorithms that will be executed on all images in this archive. Note that you can only link algorithms with an active container image.",
        }
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }


class UploadersForm(UserGroupForm):
    role = "uploader"


class UsersForm(UserGroupForm):
    role = "user"

    def add_or_remove_user(self, *, obj):
        super().add_or_remove_user(obj=obj)

        user = self.cleaned_data["user"]

        try:
            permission_request = ArchivePermissionRequest.objects.get(
                user=user, archive=obj
            )
        except ObjectDoesNotExist:
            return

        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = ArchivePermissionRequest.REJECTED
        else:
            permission_request.status = ArchivePermissionRequest.ACCEPTED

        permission_request.save()


class ArchivePermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = ArchivePermissionRequest


class ArchiveItemsToReaderStudyForm(SaveFormInitMixin, Form):
    reader_study = ModelChoiceField(
        queryset=ReaderStudy.objects.none(), required=True
    )
    items = ModelMultipleChoiceField(
        queryset=ArchiveItem.objects.none(),
        required=True,
        widget=Select2MultipleWidget,
    )

    def __init__(self, *args, user, archive, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.archive = archive

        self.fields["reader_study"].queryset = get_objects_for_user(
            self.user,
            "reader_studies.change_readerstudy",
        ).order_by("title")

        self.fields["items"].queryset = self.archive.items.all()
        self.fields["items"].initial = self.fields["items"].queryset


class AddCasesForm(UploadRawImagesForm):
    interface = ModelChoiceField(
        queryset=ComponentInterface.objects.filter(
            kind__in=InterfaceKind.interface_type_image()
        ).order_by("title"),
        widget=autocomplete.ModelSelect2(
            url="components:component-interface-autocomplete",
            attrs={
                "data-placeholder": "Search for an interface ...",
                "data-minimum-input-length": 3,
                "data-theme": settings.CRISPY_TEMPLATE_PACK,
                "data-html": True,
            },
        ),
    )

    def __init__(self, *args, interface_viewname, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["interface"].help_text = format_lazy(
            (
                'See the <a href="{}">list of interfaces</a> for more '
                "information about each interface. "
                "Please contact support if your desired interface is missing."
            ),
            reverse_lazy(interface_viewname),
        )

    def save(self, *args, **kwargs):
        self._linked_task.kwargs.update(
            {"interface_pk": self.cleaned_data["interface"].pk}
        )
        return super().save(*args, **kwargs)


class ArchiveItemFormMixin:
    class Meta:
        non_interface_fields = ("title",)

    @property
    def model(self):
        return self.base_obj.civ_set_model

    def unique_title_query(self, *args, **kwargs):
        return (
            super()
            .unique_title_query(*args, **kwargs)
            .filter(archive=self.base_obj)
        )


class ArchiveItemCreateForm(
    ArchiveItemFormMixin,
    UniqueTitleCreateFormMixin,
    CIVSetCreateFormMixin,
    MultipleCIVForm,
):
    pass


class ArchiveItemUpdateForm(
    ArchiveItemFormMixin,
    UniqueTitleUpdateFormMixin,
    CIVSetUpdateFormMixin,
    MultipleCIVForm,
):
    pass
