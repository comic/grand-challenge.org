import uuid

from dal import autocomplete
from django.contrib.auth.mixins import AccessMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, TextChoices
from django.forms import Media
from django.http import HttpResponse
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

from grandchallenge.algorithms.forms import NON_ALGORITHM_INTERFACES
from grandchallenge.api.permissions import IsAuthenticated
from grandchallenge.archives.models import Archive
from grandchallenge.components.form_fields import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.forms import CIVSetDeleteForm, SingleCIVForm
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.components.serializers import ComponentInterfaceSerializer
from grandchallenge.core.guardian import (
    ObjectPermissionCheckerMixin,
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    get_objects_for_user,
)
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.uploads.widgets import UserUploadMultipleWidget


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
    ).exclude(slug__in=NON_ALGORITHM_INTERFACES)
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
        if self.forwarded:
            object_slug = self.forwarded.pop("object")
            model_name = self.forwarded.pop("model")
            if model_name == ReaderStudy._meta.model_name:
                object = ReaderStudy.objects.get(slug=object_slug)
            elif model_name == Archive._meta.model_name:
                object = Archive.objects.get(slug=object_slug)
            else:
                raise RuntimeError(
                    f"Autocomplete for objects of type {model_name} not defined."
                )
            qs = ComponentInterface.objects.exclude(
                slug__in=object.values_for_interfaces.keys()
            ).exclude(pk__in=self.forwarded.values())
        else:
            qs = ComponentInterface.objects.filter(
                kind__in=InterfaceKind.interface_type_image()
            ).order_by("title")

        if self.q:
            qs = qs.filter(
                Q(title__icontains=self.q)
                | Q(slug__icontains=self.q)
                | Q(description__icontains=self.q)
            )

        return qs

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
            for widget in form_class._possible_widgets:
                media = media + widget().media
        if hasattr(self, "object"):
            object = self.object
        else:
            object = None
        context.update(
            {
                "base_object": self.base_object,
                "form_media": media,
                "object": object,
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
    PermissionListMixin,
    PaginatedTableListView,
):
    model = None
    permission_required = None
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
        return NotImplementedError

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
        # subset by permission
        permission = f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}"
        return get_objects_for_user(
            user=self.request.user,
            perms=[permission],
            klass=self.base_object.civ_sets_related_manager.all(),
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


class FileUploadFormFieldView(LoginRequiredMixin, AccessMixin, View):
    def dispatch(self, request, *args, **kwargs):
        algorithms = get_objects_for_user(
            self.request.user, "algorithms.execute_algorithm"
        )
        reader_studies = get_objects_for_user(
            self.request.user, "reader_studies.change_readerstudy"
        )
        archives = get_objects_for_user(
            self.request.user, "archives.change_archive"
        )

        if algorithms.exists() or reader_studies.exists() or archives.exists():
            return super().dispatch(request, *args, **kwargs)
        else:
            return self.handle_no_permission()

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
