from functools import reduce
from operator import or_

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import reverse
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormView

from grandchallenge.products.forms import ImportForm
from grandchallenge.products.models import Company, Product, Status
from grandchallenge.products.utils import DataImporter


class ProductList(ListView):
    model = Product
    context_object_name = "products"
    queryset = Product.objects.filter(ce_status=Status.CERTIFIED).order_by(
        "-verified", "-ce_verified", "product_name"
    )

    def get_queryset(self):
        queryset = super().get_queryset().select_related("company")
        subspeciality_query = self.request.GET.get("subspeciality")
        modality_query = self.request.GET.get("modality")
        ce_class_query = self.request.GET.get("ce_class")
        fda_class_query = self.request.GET.get("fda_class")
        search_query = self.request.GET.get("search")
        self.product_total_all = queryset.count()

        if search_query:
            search_fields = [
                "product_name",
                "subspeciality",
                "modality",
                "description",
                "key_features",
                "diseases",
                "distribution",
                "company__company_name",
            ]
            q = reduce(
                or_,
                [
                    Q(**{f"{f}__icontains": search_query})
                    for f in search_fields
                ],
                Q(),
            )
            queryset = queryset.filter(q)

        if subspeciality_query and subspeciality_query != "All":
            queryset = queryset.filter(
                Q(subspeciality__icontains=subspeciality_query)
            )
        if modality_query and modality_query != "All":
            queryset = queryset.filter(Q(modality__icontains=modality_query))

        if ce_class_query and ce_class_query != "All":
            queryset = queryset.filter(Q(ce_class=ce_class_query))

        if (
            fda_class_query
            and fda_class_query != "All"
            and fda_class_query != "No FDA"
        ):
            queryset = queryset.filter(Q(fda_class=fda_class_query))
        elif fda_class_query == "No FDA":
            queryset = queryset.filter(Q(fda_class=""))

        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        subspeciality_query = self.request.GET.get("subspeciality", "All")
        modality_query = self.request.GET.get("modality", "All")
        ce_class_query = self.request.GET.get("ce_class", "All")
        fda_class_query = self.request.GET.get("fda_class", "All")
        search_query = self.request.GET.get("search", "")
        subspecialities = [
            "All",
            "Abdomen",
            "Breast",
            "Cardiac",
            "Chest",
            "MSK",
            "Neuro",
            "Other",
        ]

        modalities = [
            "All",
            "X-ray",
            "CT",
            "MR",
            "Ultrasound",
            "Mammography",
            "PET",
            "Other",
        ]

        ce_classes = [
            "All",
            "Class I",
            "Class IIa",
            "Class IIb",
            "Class III",
        ]

        fda_classes = ["All", "Class I", "Class II", "Class III", "No FDA"]

        context.update(
            {
                "q_search": search_query,
                "subspecialities": subspecialities,
                "modalities": modalities,
                "ce_classes": ce_classes,
                "fda_classes": fda_classes,
                "selected_subspeciality": subspeciality_query,
                "selected_modality": modality_query,
                "selected_ce_class": ce_class_query,
                "selected_fda_class": fda_class_query,
                "products_selected_page": True,
                "product_total": context["object_list"].count(),
                "product_total_all": self.product_total_all,
            }
        )
        return context


class ProductDetail(DetailView):
    model = Product


class CompanyList(ListView):
    model = Company
    context_object_name = "companies"
    queryset = Company.objects.order_by("company_name")

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get("search")

        if search_query:
            search_fields = ["company_name", "description", "hq"]
            q = reduce(
                or_,
                [
                    Q(**{f"{f}__icontains": search_query})
                    for f in search_fields
                ],
                Q(),
            )
            queryset = queryset.filter(q)
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        search_query = self.request.GET.get("search", "")

        context.update(
            {
                "q_search": search_query,
                "companies_selected_page": True,
                "company_total": context["object_list"].count(),
            }
        )
        return context


class CompanyDetail(DetailView):
    model = Company
    context_object_name = "company"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        products_by_company = self.object.product_set.order_by(
            "ce_status", "product_name"
        )
        context.update({"products_by_company": products_by_company})

        return context


class AboutPage(TemplateView):
    template_name = "products/about.html"


class ContactPage(TemplateView):
    template_name = "products/contact.html"


class ImportDataView(PermissionRequiredMixin, FormView):
    template_name = "products/import_data.html"
    form_class = ImportForm
    permission_required = (
        f"{Product._meta.app_label}.add_{Product._meta.model_name}"
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, *args, **kwargs):
        response = super().form_valid(*args, **kwargs)
        form = self.get_form()
        if form.is_valid():
            di = DataImporter()
            di.import_data(
                product_data=form.cleaned_data["products_file"],
                company_data=form.cleaned_data["companies_file"],
                images_zip=form.cleaned_data["images_zip"][0].open(),
            )
        return response

    def get_success_url(self):
        return reverse("products:product-list")
