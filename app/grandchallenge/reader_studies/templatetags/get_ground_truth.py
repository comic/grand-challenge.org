from django import template

register = template.Library()


@register.simple_tag
def get_ground_truth(obj, image, question):
    """Get the auth token for the user."""
    ground_truths = obj.statistics["ground_truths"]
    return ground_truths[image][question]
