from functools import reduce
from operator import or_

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, TemplateView

from grandchallenge.ai_website.models import CompanyEntry, ProductEntry

# Create your views here.


class ProductList(ListView):
    model = ProductEntry
    template_name = "ai_website/product_list.html"
    context_object_name = "products"
    queryset = ProductEntry.objects.order_by("product_name")

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
        elif subspeciality_query and subspeciality_query != "All":
            queryset = queryset.filter(
                Q(subspeciality__icontains=subspeciality_query)
            )
        elif modality_query and modality_query != "All":
            queryset = queryset.filter(Q(modality__icontains=modality_query))
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
            }
        )
        return context


class ProductPage(TemplateView):
    template_name = "ai_website/product_page.html"

    def get_context_data(self, pk):
        product = get_object_or_404(ProductEntry, pk=pk)
        return {"product": product}


class CompanyList(ListView):
    template_name = "ai_website/company_list.html"
    model = CompanyEntry
    context_object_name = "companies"
    queryset = CompanyEntry.objects.order_by("company_name")

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

        # TODO: fix that all products from company are returned as variable, preferably to be called as: company.product_by_company
        products_by_companies = set()
        for company in self.queryset:
            products_by_companies.add(
                ProductEntry.objects.filter(
                    company__company_name__contains=company.company_name
                )
            )
        context.update(
            {
                "q_search": search_query,
                "products_by_companies": products_by_companies,
            }
        )
        return context


class CompanyPage(TemplateView):
    template_name = "ai_website/company_page.html"

    def get_context_data(self, pk):
        company = get_object_or_404(CompanyEntry, pk=pk)
        products_by_company = ProductEntry.objects.filter(
            company__company_name__contains=company.company_name
        ).order_by("product_name")
        return {"company": company, "products_by_company": products_by_company}


class AboutPage(TemplateView):
    template_name = "ai_website/about.html"

    def get_context_data(self):
        return


class ContactPage(TemplateView):
    template_name = "ai_website/contact.html"

    def get_context_data(self):
        return
