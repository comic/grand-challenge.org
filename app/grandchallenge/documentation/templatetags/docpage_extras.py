from urllib.parse import quote

from django import template
from django.template.defaultfilters import striptags

from grandchallenge.subdomains.utils import reverse

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


@register.simple_tag
def get_breadcrumbs(page):
    breadcrumbs = []

    current = page.parent
    while current:
        breadcrumbs.insert(
            0,
            {
                "title": current.title,
                "url": reverse(
                    "documentation:detail", kwargs={"slug": current.slug}
                ),
            },
        )
        current = current.parent

    return breadcrumbs


@register.filter
def startend_text(text):
    text = striptags(text).strip()

    if len(text) <= 40:
        return text

    # Split around center word and extract fixed-length windows
    words = text.split()
    n_words = min(3, len(words) // 2)
    start = " ".join(words[:n_words]).rstrip(":")
    end = " ".join(words[-n_words:])

    return f"{quote(start)}:::{quote(end)}"
