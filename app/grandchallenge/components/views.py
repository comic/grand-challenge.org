import uuid
from functools import reduce
from operator import or_

from dal import autocomplete
from django.contrib.auth.mixins import AccessMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, TextChoices
from django.forms import HiddenInput, Media
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.views import View
from django.views.generic import (
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.algorithms.forms import RESERVED_SOCKET_SLUGS
from grandchallenge.algorithms.models import Algorithm
from grandchallenge.api.permissions import IsAuthenticated
from grandchallenge.archives.models import Archive
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    FileWidgetChoices,
    file_upload_text,
)
from grandchallenge.components.forms import CIVSetDeleteForm, SingleCIVForm
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKinds,
)
from grandchallenge.components.serializers import ComponentInterfaceSerializer
from grandchallenge.components.widgets import FileSearchWidget
from grandchallenge.core.guardian import (
    ObjectPermissionCheckerMixin,
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    filter_by_permission,
    get_object_if_allowed,
)
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.serving.models import (
    get_component_interface_values_for_user,
)
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import (
    UserUploadMultipleWidget,
    UserUploadSingleWidget,
)


class ComponentInterfaceViewSet(ReadOnlyModelViewSet):
    serializer_class = ComponentInterfaceSerializer
    queryset = ComponentInterface.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ("slug",)
    filter_backends = (DjangoFilterBackend,)


class ComponentInterfaceIOSwitch(LoginRequiredMixin, TemplateView):
    template_name = "components/componentinterface_io_switch.html"


class InterfaceListTypeOptions(TextChoices):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    ITEM = "ITEM"
    CASE = "CASE"


class InterfaceObjectTypeOptions(TextChoices):
    ALGORITHM = "ALGORITHM"
    ARCHIVE = "ARCHIVE"
    READER_STUDY = "READER STUDY"


class ComponentInterfaceList(LoginRequiredMixin, ListView):
    model = ComponentInterface
    queryset = ComponentInterface.objects.select_related(
        "example_value"
    ).exclude(slug__in=RESERVED_SOCKET_SLUGS)
    list_type = None
    object_type = None

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "list_type": self.list_type,
                "object_type": self.object_type,
                "list_type_options": InterfaceListTypeOptions,
                "object_type_options": InterfaceObjectTypeOptions,
            }
        )
        return context


class ComponentInterfaceAutocomplete(
    LoginRequiredMixin, autocomplete.Select2QuerySetView
):
    def get_queryset(self):
        object_slug = self.forwarded.pop("object_slug")
        model_name = self.forwarded.pop("model_name")
        image_only = self.forwarded.pop("image_only", False)

        if model_name == ReaderStudy._meta.model_name:
            obj = ReaderStudy.objects.get(slug=object_slug)
        elif model_name == Archive._meta.model_name:
            obj = Archive.objects.get(slug=object_slug)
        else:
            raise RuntimeError(
                f"Autocomplete for objects of type {model_name} not defined."
            )

        try:
            extra_filter_kwargs = {"slug__in": obj.allowed_socket_slugs}
        except AttributeError:
            extra_filter_kwargs = {}

        if image_only:
            qs = ComponentInterface.objects.filter(
                kind__in=InterfaceKinds.image,
                **extra_filter_kwargs,
            )
        else:
            qs = (
                ComponentInterface.objects.all()
                .filter(**extra_filter_kwargs)
                .exclude(slug__in=obj.values_for_interfaces.keys())
                .exclude(pk__in=self.forwarded.values())
            )

        if self.q:
            qs = qs.filter(
                Q(title__icontains=self.q)
                | Q(slug__icontains=self.q)
                | Q(description__icontains=self.q)
            )

        return qs.order_by("title")

    def get_result_label(self, result):
        return result.title


class MultipleCIVProcessingBaseView(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    included_form_classes = (SingleCIVForm,)
    form_class = None
    permission_required = None
    raise_exception = True
    success_message = None

    @property
    def base_object(self):
        raise NotImplementedError

    def form_valid(self, form):
        form.process_object_data()
        response = super().form_valid(form)
        return HttpResponse(
            response.url,
            status=302,
            headers={
                "HX-Redirect": response.url,
                "HX-Refresh": True,
            },
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            instance = self.object
        else:
            instance = None
        kwargs.update(
            {
                "user": self.request.user,
                "auto_id": f"id-{uuid.uuid4()}",
                "base_obj": self.base_object,
                "instance": instance,
            }
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        media = Media()
        for form_class in self.included_form_classes:
            for widget in form_class.possible_widgets:
                media = media + widget().media
        context.update(
            {
                "base_object": self.base_object,
                "form_media": media,
                "object": getattr(self, "object", None),
            }
        )
        return context

    def get_success_message(self, cleaned_data):
        return format_html(
            "{success_message} "
            "Image and file import jobs have been queued. "
            "You will be notified about errors related to image and file imports "
            "via a <a href={url}>notification</a>.",
            success_message=self.success_message,
            url=reverse("notifications:list"),
        )


class CIVSetFormMixin:
    template_name = "components/civ_set_form.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "form_url": self.form_url,
                "new_interface_url": self.new_interface_url,
                "return_url": self.return_url,
            }
        )
        return context

    @property
    def form_url(self):
        raise NotImplementedError

    @property
    def return_url(self):
        raise NotImplementedError

    @property
    def new_interface_url(self):
        raise NotImplementedError


class InterfacesCreateBaseView(ObjectPermissionRequiredMixin, TemplateView):
    form_class = SingleCIVForm
    raise_exception = True
    template_name = "components/new_interface_create.html"

    def get_permission_object(self):
        return self.object if self.object else self.base_object

    def get_form_kwargs(self):
        return {
            "pk": self.kwargs.get("pk"),
            "base_obj": self.base_object,
            "interface": self.request.GET.get("interface"),
            "user": self.request.user,
            "auto_id": f"id-{uuid.uuid4()}",
            "htmx_url": self.get_htmx_url(),
        }

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "object": self.object,
                "form": self.form_class(**self.get_form_kwargs()),
            }
        )
        return context


class CIVSetDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = None
    permission_required = None
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "components/civ_set_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "request": self.request,
                "base_model_options": BaseModelOptions,
            }
        )
        return context


class CIVSetDelete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = None
    permission_required = None
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "components/civset_confirm_delete.html"

    def get_success_url(self):
        return self.object.base_object.civ_sets_list_url

    def get_success_message(self, cleaned_data):
        return f"{self.object._meta.verbose_name.title()} was successfully deleted"


class BaseModelOptions(TextChoices):
    ARCHIVE = Archive._meta.model_name
    READER_STUDY = ReaderStudy._meta.model_name


class CivSetListView(
    LoginRequiredMixin,
    ObjectPermissionCheckerMixin,
    ViewObjectPermissionListMixin,
    PaginatedTableListView,
):
    model = None
    raise_exception = True
    template_name = "components/civ_set_list.html"
    row_template = "components/civ_set_row.html"
    search_fields = [
        "pk",
        "title",
        "values__interface__title",
        "values__image__name",
        "values__file",
    ]
    default_sort_order = "asc"
    columns = [
        Column(title=""),
        Column(title="Detail"),
        Column(title="ID", sort_field="pk"),
        Column(title="Title", sort_field="title"),
        Column(title="Values"),
        Column(title="Viewer"),
        Column(title="Edit"),
        Column(title="Remove"),
    ]

    default_sort_column = 2

    @property
    def base_object(self):
        raise NotImplementedError

    def get_context_data(self, *args, object_list=None, **kwargs):
        context = super().get_context_data(*args, object_list=None, **kwargs)

        if object_list:
            self.permission_checker.prefetch_perms(objects=object_list)

        context.update(
            {
                "base_object": self.base_object,
                "base_model_options": BaseModelOptions,
                "request": self.request,
            }
        )
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related(
            "values", "values__image", "values__interface"
        )


class CIVSetBulkDelete(LoginRequiredMixin, FormView):
    form_class = CIVSetDeleteForm
    model = None
    template_name = "components/civ_set_delete_confirm.html"

    @property
    def base_object(self):
        raise NotImplementedError

    def get_success_url(self):
        return self.base_object.civ_sets_list_url

    def get_queryset(self, *args, **kwargs):
        return filter_by_permission(
            queryset=self.base_object.civ_sets_related_manager.all(),
            user=self.request.user,
            codename=f"delete_{self.model._meta.model_name}",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "base_object": self.base_object,
                "delete_count": (self.selected_objects.count()),
            }
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "queryset": (
                    self.selected_objects
                    if self.selected_objects
                    else self.get_queryset()
                ),
            }
        )
        return kwargs

    @cached_property
    def selected_objects(self):
        # Selecting happens on the ListView through a GET request to this view
        # on POST the selected objects are part of the form field
        if self.request.method == "GET":
            delete_all = self.request.GET.get("delete-all", None)
            if delete_all:
                return self.get_queryset()
            else:
                selected = self.request.GET.getlist(
                    "selected-for-deletion", None
                )
                # filtering the original queryset
                # so that only objects with permission are included
                return self.get_queryset().filter(pk__in=selected)
        else:
            return self.model.objects.none()

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def form_valid(self, form):
        for civ_set in form.cleaned_data["civ_sets_to_delete"]:
            civ_set.delete()
        return super().form_valid(form)


class FileAccessRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        algorithms = filter_by_permission(
            queryset=Algorithm.objects.all(),
            user=self.request.user,
            codename="execute_algorithm",
        )
        reader_studies = filter_by_permission(
            queryset=ReaderStudy.objects.all(),
            user=self.request.user,
            codename="change_readerstudy",
        )
        archives = filter_by_permission(
            queryset=Archive.objects.all(),
            user=self.request.user,
            codename="change_archive",
        )

        if algorithms.exists() or reader_studies.exists() or archives.exists():
            return super().dispatch(request, *args, **kwargs)
        else:
            return self.handle_no_permission()


class FileUploadFormFieldView(
    LoginRequiredMixin, FileAccessRequiredMixin, View
):
    @cached_property
    def interface(self):
        return get_object_or_404(
            ComponentInterface, slug=self.kwargs["interface_slug"]
        )

    def get(self, request, *args, **kwargs):
        widget_name = f"{INTERFACE_FORM_FIELD_PREFIX}{self.interface.slug}"
        html_content = render_to_string(
            UserUploadMultipleWidget.template_name,
            {
                "widget": UserUploadMultipleWidget(
                    allowed_file_types=self.interface.allowed_file_types,
                ).get_context(
                    name=widget_name,
                    value=None,
                    attrs={
                        "id": widget_name,
                        "help_text": clean(self.interface.description),
                    },
                )[
                    "widget"
                ],
            },
        )
        return HttpResponse(html_content)


class FileWidgetSelectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        prefixed_interface_slug = self.request.GET.get(
            "prefixed-interface-slug"
        )
        interface = get_object_or_404(
            ComponentInterface,
            slug=prefixed_interface_slug.replace(
                INTERFACE_FORM_FIELD_PREFIX, ""
            ),
        )
        widget_choice_name = request.GET.get(
            f"widget-choice-{prefixed_interface_slug}"
        )
        try:
            widget_choice = FileWidgetChoices(widget_choice_name)
        except ValueError:
            raise Http404(f"Widget choice {widget_choice_name} not found")
        current_value_pk = request.GET.get("current-value-pk")

        if widget_choice == FileWidgetChoices.FILE_SEARCH:
            return HttpResponse(
                FileSearchWidget().render(
                    name=prefixed_interface_slug,
                    value=None,
                )
            )
        elif widget_choice == FileWidgetChoices.FILE_UPLOAD:
            return HttpResponse(
                UserUploadSingleWidget().render(
                    name=prefixed_interface_slug,
                    value=None,
                    attrs={
                        "id": prefixed_interface_slug,
                        "help_text": f"{file_upload_text} {interface.file_extension}",
                    },
                )
            )
        elif widget_choice == FileWidgetChoices.FILE_SELECTED:
            if current_value_pk and (
                get_component_interface_values_for_user(
                    user=request.user, civ_pk=current_value_pk
                ).exists()
                if current_value_pk.isdigit()
                else get_object_if_allowed(
                    model=UserUpload,
                    pk=current_value_pk,
                    user=request.user,
                    codename="change_userupload",
                )
            ):
                # this can happen on the display set update view or redisplay of
                # form upon validation, where one of the options is the current
                # file, this enables switching back from one of the above widgets
                # to the chosen file. This makes sure the form element with the
                # right name is available on resubmission.
                return HttpResponse(
                    HiddenInput().render(
                        name=prefixed_interface_slug,
                        value=current_value_pk,
                    )
                )
            raise Http404(f"Selected file {current_value_pk} not found")
        elif widget_choice == FileWidgetChoices.UNDEFINED:
            # this happens when switching back from one of the
            # above widgets to the "Choose data source" option
            return HttpResponse()
        raise NotImplementedError(
            f"Response for widget choice {widget_choice} not implemented"
        )


class FileSearchResultView(
    LoginRequiredMixin, FileAccessRequiredMixin, ListView
):
    template_name = "components/file_search_result_select.html"
    search_fields = ["pk", "file"]
    model = ComponentInterfaceValue
    paginate_by = 50

    def __init__(self):
        super().__init__()
        self.interface = None

    def get_queryset(self):
        return get_component_interface_values_for_user(
            user=self.request.user,
            interface=self.interface,
        )

    def get(self, request, *args, **kwargs):
        prefixed_interface_slug = request.GET.get("prefixed-interface-slug")
        self.interface = get_object_or_404(
            ComponentInterface,
            slug=prefixed_interface_slug.replace(
                INTERFACE_FORM_FIELD_PREFIX, ""
            ),
        )

        qs = self.get_queryset()
        query = request.GET.get("query-" + prefixed_interface_slug)
        if query:
            q = reduce(
                or_,
                [Q(**{f"{f}__icontains": query}) for f in self.search_fields],
                Q(),
            )
            qs = qs.filter(q).order_by("file")
        self.object_list = qs
        return self.render_to_response(self.get_context_data(**kwargs))
