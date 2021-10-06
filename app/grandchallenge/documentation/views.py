from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.documentation.models import DocPage


class DocPageList(ListView):
    model = DocPage


class DocPageDetail(DetailView):
    model = DocPage

    def get_context_object_name(self, obj):
        return "currentdocpage"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        firstdocpage = DocPage.objects.first()
        top_level_pages = (
            DocPage.objects.filter(parent__isnull=True)
            .prefetch_related("children__children")
            .order_by("order")
            .all()
        )

        context.update(
            {
                "firstdocpage": firstdocpage,
                "top_level_pages": top_level_pages,
                "cleaned_content": clean(self.object.content),
            }
        )

        return context


class DocumentationHome(DocPageDetail):
    def get_object(self, queryset=None):
        return get_object_or_404(DocPage, order=1)
