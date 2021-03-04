import json

from rest_framework.settings import api_settings
from rest_framework.utils.encoders import JSONEncoder
from rest_framework_csv.renderers import CSVRenderer


class PaginatedCSVRenderer(CSVRenderer):
    results_field = "results"

    def render(self, data, *args, **kwargs):
        if self.results_field in data:
            data = data[self.results_field]

        return super().render(data, *args, **kwargs)

    def flatten_data(self, data):
        """
        Create a dictionary that is 1 level deep, with nested values serialized
        as json. This means that the header rows are now consistent.
        """
        for row in data:
            flat_row = {k: self._flatten_value(v) for k, v in row.items()}
            yield flat_row

    @staticmethod
    def _flatten_value(value):
        if isinstance(value, (dict, list)):
            return json.dumps(
                value,
                cls=JSONEncoder,
                ensure_ascii=not api_settings.UNICODE_JSON,
                allow_nan=not api_settings.STRICT_JSON,
            )
        else:
            return value
