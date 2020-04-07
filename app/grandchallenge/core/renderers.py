from rest_framework_csv.renderers import CSVRenderer


class PaginatedCSVRenderer(CSVRenderer):
    """Paginated renderer for list views"""

    results_field = "results"

    def render(self, data, *args, **kwargs):
        if hasattr(data, self.results_field):
            data = data.get([self.results_field])

        return super().render(data, *args, **kwargs)
