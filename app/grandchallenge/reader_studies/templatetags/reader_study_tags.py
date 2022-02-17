from django import template

register = template.Library()


@register.simple_tag
def get_ground_truth(reader_study, image, question):
    """Get the ground truth value for the image/question combination in reader_study."""
    ground_truths = reader_study.statistics["ground_truths"]
    return ground_truths[image][question]


@register.simple_tag
def get_values_for_interface(display_set, interface):
    """Get all values available for `interface` in `display_set`'s reader study."""
    return display_set.values_for_interface(interface)
