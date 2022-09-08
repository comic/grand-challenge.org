import csv
import io
import json
import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Div,
    Field,
    Fieldset,
    Layout,
    Submit,
)
from dal import autocomplete
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.transaction import on_commit
from django.forms import (
    BooleanField,
    CharField,
    FileField,
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    Select,
    Textarea,
    TextInput,
)
from django.forms.models import inlineformset_factory
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget
from dynamic_forms import DynamicField, DynamicFormMixin
from guardian.shortcuts import get_objects_for_user

from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.layout import Formset
from grandchallenge.core.widgets import JSONEditorWidget, MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.forms import ViewContentMixin
from grandchallenge.reader_studies.models import (
    ANSWER_TYPE_TO_INTERFACE_KIND_MAP,
    CASE_TEXT_SCHEMA,
    AnswerType,
    CategoricalOption,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)
from grandchallenge.reader_studies.tasks import add_file_to_display_set
from grandchallenge.reader_studies.widgets import SelectUploadWidget
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget
from grandchallenge.workstation_configs.models import OVERLAY_SEGMENTS_SCHEMA

logger = logging.getLogger(__name__)

READER_STUDY_HELP_TEXTS = {
    "title": "The title of this reader study.",
    "logo": "The logo for this reader study.",
    "social_image": "An image for this reader study which is displayed when posting the reader study link on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
    "description": "Describe what this reader study is for.",
    "workstation": (
        "Which viewer should be used for this reader study? "
        "Note that in order to add a viewer you must be a member "
        "of that viewers users group. "
        "If you do not see the viewer that you want to use, "
        "please contact the admin for that viewer."
    ),
    "workstation_config": format_lazy(
        (
            "The viewer configuration to use for this reader study. "
            "If a suitable configuration does not exist you can "
            '<a href="{}">create a new one</a>. For a list of existing '
            'configurations, go <a href="{}">here</a>.'
        ),
        reverse_lazy("workstation-configs:create"),
        reverse_lazy("workstation-configs:list"),
    ),
    "help_text_markdown": (
        "Extra information that will be presented to the reader in the help "
        "text modal and on the reader study detail page."
    ),
    "publications": format_lazy(
        (
            "The publications associated with this reader study. "
            'If your publication is missing click <a href="{}">here</a> to add it '
            "and then refresh this page."
        ),
        reverse_lazy("publications:create"),
    ),
}


class ReaderStudyCreateForm(
    WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm
):
    class Meta:
        model = ReaderStudy
        fields = (
            "title",
            "logo",
            "social_image",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "workstation",
            "workstation_config",
            "is_educational",
            "public",
            "access_request_handling",
            "allow_answer_modification",
            "shuffle_hanging_list",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
        )
        help_texts = READER_STUDY_HELP_TEXTS
        widgets = {
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }

    def clean(self):
        super().clean()
        if (
            self.cleaned_data["allow_answer_modification"]
            and not self.cleaned_data["allow_case_navigation"]
        ):
            self.add_error(
                error=ValidationError(
                    "Case navigation is required when answer modification is allowed",
                    code="invalid",
                ),
                field=None,
            )
        if self.cleaned_data["roll_over_answers_for_n_cases"] > 0 and (
            self.cleaned_data["allow_case_navigation"]
            or self.cleaned_data["shuffle_hanging_list"]
        ):
            self.add_error(
                error=ValidationError(
                    "Rolling over answers should not be used together with case navigation or shuffling of the hanging list",
                    code="invalid",
                ),
                field=None,
            )


class ReaderStudyUpdateForm(
    ReaderStudyCreateForm, ModelForm, ViewContentMixin
):
    class Meta(ReaderStudyCreateForm.Meta):
        fields = (
            "title",
            "logo",
            "social_image",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "workstation",
            "workstation_config",
            "hanging_protocol",
            "view_content",
            "help_text_markdown",
            "shuffle_hanging_list",
            "is_educational",
            "public",
            "access_request_handling",
            "allow_answer_modification",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
            "case_text",
        )
        widgets = {
            "case_text": JSONEditorWidget(schema=CASE_TEXT_SCHEMA),
            "help_text_markdown": MarkdownEditorWidget,
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        widgets.update(ViewContentMixin.Meta.widgets)
        help_texts = {
            **READER_STUDY_HELP_TEXTS,
            "shuffle_hanging_list": (
                "If true, the order of the display sets will be uniquely shuffled "
                "for each reader. If false, the display sets will be "
                "ordered by the Order field that you have set on each display set."
            ),
            "case_text": (
                "Free text that can be included for each case, where the key "
                "is the filename and the value is free text. You can use "
                "markdown formatting in the text. Not all images in the "
                "reader study are required. "
                'e.g., {"a73512ee-1.2.276.0.542432.3.1.3.3546325986342": "This is *image 1*"}'
            ),
            "hanging_protocol": format_lazy(
                (
                    "The hanging protocol to use for this reader study. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }
        help_texts.update(ViewContentMixin.Meta.help_texts)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["view_content"].help_text += (
            " The following interfaces are used in your reader study: "
            f"{', '.join(self.instance.display_sets.values_list('values__interface__slug', flat=True).order_by().distinct())}."
        )


class ReaderStudyCopyForm(Form):
    title = CharField(required=True)
    description = CharField(required=False, widget=Textarea())
    copy_display_sets = BooleanField(required=False, initial=True)
    copy_hanging_protocol = BooleanField(required=False, initial=True)
    copy_view_content = BooleanField(required=False, initial=True)
    copy_case_text = BooleanField(required=False, initial=True)
    copy_questions = BooleanField(required=False, initial=True)
    copy_readers = BooleanField(required=False, initial=True)
    copy_editors = BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Copy"))


class QuestionForm(SaveFormInitMixin, DynamicFormMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Div(
                Field("question_text"),
                Field("help_text"),
                Field("answer_type"),
                Fieldset(
                    "Add options",
                    Formset("options"),
                    css_class="options-formset",
                ),
                Field("required"),
                Field("image_port"),
                Field("direction"),
                Field("order"),
                Field("interface"),
                Field("overlay_segments"),
                Field("look_up_table"),
                HTML("<br>"),
                ButtonHolder(Submit("save", "Save")),
            )
        )

    def interface_choices(self):
        answer_type = self["answer_type"].value()
        if answer_type is None:
            return ComponentInterface.objects.none()
        return ComponentInterface.objects.filter(
            kind__in=ANSWER_TYPE_TO_INTERFACE_KIND_MAP[answer_type]
        )

    def initial_interface(self):
        return self.interface_choices().first()

    def clean(self):
        answer_type = self.cleaned_data.get("answer_type")
        interface = self.cleaned_data.get("interface")
        overlay_segments = self.cleaned_data.get("overlay_segments")

        if overlay_segments and answer_type != AnswerType.MASK:
            self.add_error(
                error=ValidationError(
                    "Overlay segments should only be set for Mask answers"
                ),
                field=None,
            )

        if interface and overlay_segments != interface.overlay_segments:
            self.add_error(
                error=ValidationError(
                    f"Overlay segments do not match those of {interface.title}. "
                    f"Please use {json.dumps(interface.overlay_segments)}."
                ),
                field=None,
            )
        return super().clean()

    def full_clean(self):
        """Override of the form's full_clean method.

        Some fields are made readonly once the question has been answered.
        Because disabled fields do not get included in the post data, this
        causes issues with required fields. Therefore we populate them here.
        """
        data = self.data.copy()
        for field in self.instance.read_only_fields:
            data[field] = getattr(self.instance, field)
        self.data = data
        return super().full_clean()

    class Meta:
        model = Question
        fields = (
            "question_text",
            "help_text",
            "answer_type",
            "required",
            "image_port",
            "direction",
            "order",
            "interface",
            "overlay_segments",
            "look_up_table",
        )
        help_texts = {
            "question_text": (
                "The question that will be presented to the user, "
                "should be short. "
                "e.g. 'Is there pathology present in these images?'"
            ),
            "help_text": (
                "This can be used to provide extra information or "
                "clarification to the reader about this question."
            ),
            "answer_type": "The type of answer that the user will give.",
            "image_port": (
                "If the user will make a bounding box or measurement, "
                "on which image port should they do it? "
                "Note, "
                "that this will be the same image port for every hanging."
            ),
            "direction": (
                "The format of the question, "
                "vertical means that the question text "
                "goes above the answer box, "
                "horizontal means that the question text "
                "will be on the same row as the answer box."
            ),
            "order": (
                "Where should this question be in the form? "
                "Lower numbers put this question to the top."
            ),
            "required": (
                "If true, the user must answer this question, otherwise the "
                "user can skip it."
            ),
            "interface": (
                "Select component interface to use as a default answer for this "
                "question."
            ),
        }
        widgets = {
            "question_text": TextInput,
            "overlay_segments": JSONEditorWidget(
                schema=OVERLAY_SEGMENTS_SCHEMA
            ),
            "answer_type": Select(
                attrs={
                    "hx-get": reverse_lazy(
                        "reader-studies:question-interfaces"
                    ),
                    "hx-target": "#id_interface",
                }
            ),
        }

    interface = DynamicField(
        ModelChoiceField,
        queryset=interface_choices,
        initial=initial_interface,
        required=False,
    )


class CategoricalOptionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].label = False

    class Meta:
        model = CategoricalOption
        fields = ("title", "default")


CategoricalOptionFormSet = inlineformset_factory(
    Question,
    CategoricalOption,
    form=CategoricalOptionForm,
    fields=["title", "default"],
    extra=1,
    can_delete=True,
)


class ReadersForm(UserGroupForm):
    role = "reader"

    def add_or_remove_user(self, *, obj):
        super().add_or_remove_user(obj=obj)

        user = self.cleaned_data["user"]

        try:
            permission_request = ReaderStudyPermissionRequest.objects.get(
                user=user, reader_study=obj
            )
        except ObjectDoesNotExist:
            return

        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = ReaderStudyPermissionRequest.REJECTED
        else:
            permission_request.status = ReaderStudyPermissionRequest.ACCEPTED

        permission_request.save()


class ReaderStudyPermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = ReaderStudyPermissionRequest


class GroundTruthForm(SaveFormInitMixin, Form):
    ground_truth = FileField(
        required=True,
        help_text="A csv file with a headers row containing the header `images`"
        " and the question text for each of the questions in this study."
        " The subsequent rows should then be filled with the image file"
        " names (separated by semicolons) and the answer corresponding to"
        " the question text provided in the header.",
    )

    def __init__(self, *args, reader_study, **kwargs):
        super().__init__(*args, **kwargs)
        self.reader_study = reader_study

    def clean_ground_truth(self):
        csv_file = self.cleaned_data.get("ground_truth")
        csv_file.seek(0)
        rdr = csv.DictReader(
            io.StringIO(csv_file.read().decode("utf-8")),
            quoting=csv.QUOTE_ALL,
            escapechar="\\",
            quotechar="'",
        )
        headers = rdr.fieldnames
        if sorted(
            filter(lambda x: not x.endswith("__explanation"), headers)
        ) != sorted(self.reader_study.ground_truth_file_headers):
            raise ValidationError(
                f"Fields provided do not match with reader study. Fields should "
                f"be: {','.join(self.reader_study.ground_truth_file_headers)}"
            )

        values = [x for x in rdr]

        return values


class DisplaySetCreateForm(Form):
    _possible_widgets = {
        *InterfaceFormField._possible_widgets,
    }

    def __init__(self, *args, instance, reader_study, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.instance = instance
        self.reader_study = reader_study
        self.user = user

        for slug, values in reader_study.values_for_interfaces.items():
            current_value = None

            if instance:
                current_value = instance.values.filter(
                    interface__slug=slug
                ).first()

            interface = ComponentInterface.objects.get(slug=slug)

            if interface.is_image_kind:
                self.fields[slug] = self._get_image_field(
                    interface=interface,
                    values=values,
                    current_value=current_value,
                )
            elif interface.requires_file:
                self.fields[slug] = self._get_file_field(
                    interface=interface,
                    values=values,
                    current_value=current_value,
                )
            else:
                self.fields[slug] = self._get_default_field(
                    interface=interface, current_value=current_value
                )

        self.fields["order"] = IntegerField(
            initial=(
                instance.order
                if instance
                else reader_study.next_display_set_order
            )
        )

    def _get_image_field(self, *, interface, values, current_value):
        return self._get_default_field(
            interface=interface, current_value=current_value
        )

    def _get_file_field(self, *, interface, values, current_value):
        return self._get_default_field(
            interface=interface, current_value=current_value
        )

    def _get_default_field(self, *, interface, current_value):
        return InterfaceFormField(
            instance=interface,
            initial=current_value.value if current_value else None,
            required=False,
            user=self.user,
        ).field


class DisplaySetUpdateForm(DisplaySetCreateForm):
    _possible_widgets = {
        SelectUploadWidget,
        *DisplaySetCreateForm._possible_widgets,
    }

    def _get_image_field(self, *, interface, values, current_value):
        return self._get_select_upload_widget_field(
            interface=interface, values=values, current_value=current_value
        )

    def _get_file_field(self, *, interface, values, current_value):
        return self._get_select_upload_widget_field(
            interface=interface, values=values, current_value=current_value
        )

    def _get_select_upload_widget_field(
        self, *, interface, values, current_value
    ):
        return ModelChoiceField(
            queryset=ComponentInterfaceValue.objects.filter(id__in=values),
            initial=current_value,
            required=False,
            widget=SelectUploadWidget(
                attrs={
                    "reader_study_slug": self.reader_study.slug,
                    "display_set_pk": self.instance.pk,
                    "interface_slug": interface.slug,
                }
            ),
        )


class FileForm(Form):

    _possible_widgets = {
        UserUploadSingleWidget,
    }

    user_upload = ModelChoiceField(
        label="File",
        queryset=None,
    )

    def __init__(
        self, *args, user, display_set, interface, instance=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.fields["user_upload"].widget = UserUploadSingleWidget(
            allowed_file_types=interface.file_mimetypes
        )
        self.fields["user_upload"].queryset = get_objects_for_user(
            user, "uploads.change_userupload", accept_global_perms=False
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        self.interface = interface
        self.display_set = display_set

    def save(self):
        civ = self.display_set.values.get(interface=self.interface)
        user_upload = self.cleaned_data["user_upload"]
        on_commit(
            lambda: add_file_to_display_set.apply_async(
                kwargs={
                    "user_upload_pk": str(user_upload.pk),
                    "interface_pk": str(self.interface.pk),
                    "display_set_pk": str(self.display_set.pk),
                    "civ_pk": str(civ.pk),
                }
            )
        )
        return civ


class DisplaySetInterfacesCreateForm(Form):
    _possible_widgets = {
        *InterfaceFormField._possible_widgets,
        autocomplete.ModelSelect2,
        Select,
    }

    def __init__(self, *args, pk, interface, reader_study, user, **kwargs):
        super().__init__(*args, **kwargs)
        selected_interface = None
        if interface:
            selected_interface = ComponentInterface.objects.get(pk=interface)
        data = kwargs.get("data")
        if data and data.get("interface"):
            selected_interface = ComponentInterface.objects.get(
                pk=data["interface"]
            )
        qs = ComponentInterface.objects.exclude(
            slug__in=reader_study.values_for_interfaces.keys()
        )
        widget_kwargs = {}
        attrs = {}
        if pk is None and selected_interface is not None:
            widget = Select
        else:
            widget = autocomplete.ModelSelect2
            attrs.update(
                {
                    "data-placeholder": "Search for an interface ...",
                    "data-minimum-input-length": 3,
                    "data-theme": settings.CRISPY_TEMPLATE_PACK,
                    "data-html": True,
                }
            )
            widget_kwargs[
                "url"
            ] = "components:component-interface-autocomplete"
            widget_kwargs["forward"] = ["interface"]

        if pk is not None:
            attrs.update(
                {
                    "hx-get": reverse_lazy(
                        "reader-studies:display-set-interfaces-create",
                        kwargs={"pk": pk, "slug": reader_study.slug},
                    ),
                    "hx-target": f"#ds-content-{pk}",
                    "hx-trigger": "interfaceSelected",
                }
            )
        else:
            attrs.update(
                {
                    "hx-get": reverse_lazy(
                        "reader-studies:display-set-new-interfaces-create",
                        kwargs={"slug": reader_study.slug},
                    ),
                    "hx-target": f"#form-{kwargs['auto_id'][:-3]}",
                    "hx-swap": "outerHTML",
                    "hx-trigger": "interfaceSelected",
                    "disabled": selected_interface is not None,
                }
            )
        widget_kwargs["attrs"] = attrs

        self.fields["interface"] = ModelChoiceField(
            initial=selected_interface,
            queryset=qs,
            widget=widget(**widget_kwargs),
        )

        if selected_interface is not None:
            self.fields["value"] = InterfaceFormField(
                instance=selected_interface,
                user=user,
            ).field
