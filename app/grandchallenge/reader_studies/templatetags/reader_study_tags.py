import os

from django import template

register = template.Library()


@register.simple_tag
def get_ground_truth(reader_study, image, question):
    """Get the ground truth value for the image/question combination in reader_study."""
    ground_truths = reader_study.statistics["ground_truths"]
    return ground_truths[image][question]


@register.filter
def filename(value):
    return os.path.basename(value.file.name)
