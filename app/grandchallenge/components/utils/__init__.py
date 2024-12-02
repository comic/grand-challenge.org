from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class GPUTypeChoices(TextChoices):
    NO_GPU = "", _("No GPU")
    A100 = "A100", _("NVIDIA A100 Tensor Core GPU")
    A10G = "A10G", _("NVIDIA A10G Tensor Core GPU")
    V100 = "V100", _("NVIDIA V100 Tensor Core GPU")
    K80 = "K80", _("NVIDIA K80 GPU")
    T4 = "T4", _("NVIDIA T4 Tensor Core GPU")


def get_default_gpu_type_choices():
    return [GPUTypeChoices.NO_GPU, GPUTypeChoices.T4]


SELECTABLE_GPU_TYPES_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "array",
    "title": "The Selectable GPU Types Schema",
    "items": {
        "enum": GPUTypeChoices.values,
        "type": "string",
    },
    "uniqueItems": True,
}
