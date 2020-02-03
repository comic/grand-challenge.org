from functools import reduce
from operator import or_

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, reverse
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import FormView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.ai_website.forms import ImportForm
from grandchallenge.ai_website.models import CompanyEntry, ProductEntry
from grandchallenge.ai_website.utils import DataImporter

# Create your views here.


class ProductList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ProductEntry
    template_name = "ai_website/product_list.html"
    context_object_name = "products"
    queryset = ProductEntry.objects.order_by("product_name")
    permission_required = (
        f"{ProductEntry._meta.app_label}.view_{ProductEntry._meta.model_name}"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        subspeciality_query = self.request.GET.get("subspeciality")
        modality_query = self.request.GET.get("modality")
        search_query = self.request.GET.get("search")

        if search_query:
            search_fields = [
                "product_name",
                "subspeciality",
                "modality",
                "description",
                "key_features",
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
        self.queryset = queryset
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        subspeciality_query = self.request.GET.get("subspeciality", "All")
        modality_query = self.request.GET.get("modality", "All")
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
            "MRI",
            "Ultrasound",
            "Mammography",
            "PET",
            "Other",
        ]

        context.update(
            {
                "q_search": search_query,
                "subspecialities": subspecialities,
                "modalities": modalities,
                "selected_subspeciality": subspeciality_query,
                "selected_modality": modality_query,
                "products_selected_page": True,
                "product_total": len(self.queryset),
            }
        )
        return context


class ProductPage(TemplateView):
    template_name = "ai_website/product_page.html"
    permission_required = (
        f"{ProductEntry._meta.app_label}.view_{ProductEntry._meta.model_name}"
    )

    def get_context_data(self, pk):
        product = get_object_or_404(ProductEntry, pk=pk)
        return {"product": product}


class CompanyList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "ai_website/company_list.html"
    model = CompanyEntry
    context_object_name = "companies"
    queryset = CompanyEntry.objects.order_by("company_name")
    permission_required = (
        f"{ProductEntry._meta.app_label}.view_{ProductEntry._meta.model_name}"
    )

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
                "company_total": len(self.queryset),
            }
        )
        return context


class CompanyPage(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "ai_website/company_page.html"
    permission_required = (
        f"{ProductEntry._meta.app_label}.view_{ProductEntry._meta.model_name}"
    )

    def get_context_data(self, pk):
        company = get_object_or_404(CompanyEntry, pk=pk)
        products_by_company = ProductEntry.objects.filter(
            company__company_name__contains=company.company_name
        ).order_by("product_name")
        return {"company": company, "products_by_company": products_by_company}


class AboutPage(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "ai_website/about.html"
    permission_required = (
        f"{ProductEntry._meta.app_label}.view_{ProductEntry._meta.model_name}"
    )


class ContactPage(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "ai_website/contact.html"
    permission_required = (
        f"{ProductEntry._meta.app_label}.view_{ProductEntry._meta.model_name}"
    )


class ImportDataView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = "ai_website/import_data.html"
    form_class = ImportForm
    permission_required = (
        f"{ProductEntry._meta.app_label}.add_{ProductEntry._meta.model_name}"
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
        return reverse("ai-website:product_list")
