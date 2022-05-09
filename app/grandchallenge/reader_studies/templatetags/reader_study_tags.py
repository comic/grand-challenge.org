import os

from django import template

register = template.Library()


@register.simple_tag
def get_ground_truth(reader_study, display_set, question):
    """Get the ground truth value for the display_set/question combination in reader_study."""
    ground_truths = reader_study.statistics["ground_truths"]
    return ground_truths[display_set][question]


@register.filter
def filename(value):
    return os.path.basename(value)
