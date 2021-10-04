from django import template

register = template.Library()


@register.simple_tag
def get_grandchildren(page):
    grandchildren = []
    for child in page.children.all():
        for grandchild in child.children.all():
            grandchildren.append(grandchild)
    return grandchildren
