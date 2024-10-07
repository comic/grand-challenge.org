import json

from rest_framework.settings import api_settings
from rest_framework.utils.encoders import JSONEncoder
from rest_framework_csv.renderers import PaginatedCSVRenderer


class RegistrationRequestCSVRenderer(PaginatedCSVRenderer):
    def flatten_dict(self, d):
        partial_flat_dict = {}
        for key, item in d.items():
            if key == "registration_question_answers":
                partial_flat_dict[key] = (
                    self.flatten_registration_question_answers(item)
                )

        d.update(partial_flat_dict)
        return super().flatten_dict(d)

    def flatten_registration_question_answers(self, answers):
        """
        Answers are potentially rich JSON objects,
         and should not be traversed during tablization
        """
        for answer in answers:
            answer["answer"] = json.dumps(
                answer["answer"],
                cls=JSONEncoder,
                ensure_ascii=not api_settings.UNICODE_JSON,
                allow_nan=not api_settings.STRICT_JSON,
            )
        return self.flatten_item(answers)
