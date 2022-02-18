from django import template

register = template.Library()


@register.simple_tag
def get_subordinate_pages(page):
    subordinate_pages = []
    for child in page.children.all():
        subordinate_pages.append(child)
        for grandchild in child.children.all():
            subordinate_pages.append(grandchild)
            for greatgrandchild in grandchild.children.all():
                subordinate_pages.append(greatgrandchild)
    return subordinate_pages
