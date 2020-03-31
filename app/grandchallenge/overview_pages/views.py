from django.views.generic import DetailView

from grandchallenge.overview_pages.models import OverviewPage


class OverviewPageDetail(DetailView):
    model = OverviewPage

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "object_list": [
                    *self.object.archives.all(),
                    *self.object.reader_studies.all(),
                    *self.object.challenges.all(),
                    *self.object.algorithms.all(),
                ]
            }
        )

        return context
