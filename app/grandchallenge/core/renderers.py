from rest_framework_csv.renderers import CSVRenderer


class PaginatedCSVRenderer(CSVRenderer):
    results_field = "results"

    def render(self, data, *args, **kwargs):
        if self.results_field in data:
            data = data[self.results_field]

        return super().render(data, *args, **kwargs)
