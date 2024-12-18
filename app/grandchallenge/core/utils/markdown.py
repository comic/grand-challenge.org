from bs4 import BeautifulSoup
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from markdown import Extension
from markdown.treeprocessors import Treeprocessor


class ExtendTagClasses:
    def __init__(self, tag_classes):
        self.tag_class_dict = tag_classes

    def __call__(self, html):
        input_is_safe = isinstance(html, SafeString)

        soup = BeautifulSoup(html, "html.parser")
        for tag, classes in self.tag_class_dict.items():

            # Make extensions safe
            classes = [escape(c).strip() for c in classes]

            # Add extension to the class attribute
            for element in soup.find_all(tag):
                current_classes = element.get("class", [])
                element["class"] = [*current_classes, *classes]

        new_html = str(soup)

        if input_is_safe:
            new_html = mark_safe(new_html)

        return mark_safe(new_html)


class LinkBlankTargetExtension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.registerExtension(self)
        md.treeprocessors.register(
            LinkBlankTargetTreeprocessor(md), "link_blank_target_extension", 0
        )


class LinkBlankTargetTreeprocessor(Treeprocessor):
    def run(self, root):
        for el in root.iter():
            if el.tag == "a":
                el.set("target", "_blank")
                el.set("rel", "noopener")
