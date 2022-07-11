import os

from django import template

register = template.Library()


@register.simple_tag
def get_ground_truth(reader_study, display_set, question):
    """Get the ground truth value for the display_set/question combination in reader_study."""
    ground_truths = reader_study.statistics["ground_truths"]
    try:
        return ground_truths[display_set][question]
    except KeyError:
        # No gt exists for this display set or question yet
        return ""


@register.filter
def filename(value):
    return os.path.basename(value)
