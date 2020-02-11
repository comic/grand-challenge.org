from django import template

register = template.Library()


@register.simple_tag
def get_ground_truth(obj, image, question):
    """Get the ground truth value for the image/question combination in reader
    study obj."""
    ground_truths = obj.statistics["ground_truths"]
    return ground_truths[image][question]
