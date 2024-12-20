from bs4 import BeautifulSoup
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe
from markdown import Extension
from markdown.treeprocessors import Treeprocessor


class BeautifulSoupWithCharEntities(BeautifulSoup):
    """
    Soup generator that elegantly handles reserved HTML entity placeholders.

    For instance, the soup HTMLparser replaces these (e.g. '&lt;') into their
    unicode equivalents (e.g. '<').

    This messes up things if the HTML is decoded into a string again.
    """

    def __init__(self, /, markup, features="html.parser", **kwargs):
        markup = markup.replace("&", "&amp;")

        super().__init__(markup=markup, features=features, **kwargs)

    def decode(self, **kwargs):
        # Prevent entity subsitution (e.g. "&" -> "&amp")
        kwargs["formatter"] = None
        return super().decode(**kwargs)


class ExtendHTMLTagClasses:
    def __init__(self, tag_classes):
        # Make extensions safe
        self.tag_class_dict = {
            t: [escape(c).strip() for c in classes]
            for t, classes in tag_classes.items()
        }

    def __call__(self, html):
        input_is_safe = isinstance(html, SafeString)

        soup = BeautifulSoupWithCharEntities(markup=html)

        for element in soup.find_all(self.tag_class_dict.keys()):
            classes = element.get("class", [])
            for new_class in self.tag_class_dict[element.name]:
                if new_class not in classes:
                    classes.append(new_class)
            element["class"] = classes

        new_markup = soup.decode()

        if input_is_safe:
            new_markup = mark_safe(new_markup)

        return new_markup


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
