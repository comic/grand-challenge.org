from xml.etree import ElementTree

from bs4 import BeautifulSoup
from markdown import Extension
from markdown.treeprocessors import Treeprocessor


class BS4Extension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.registerExtension(self)
        md.treeprocessors.register(BS4Treeprocessor(md), "bs4_extension", 0)


class BS4Treeprocessor(Treeprocessor):

    def run(self, root):

        el_class_dict = {
            "img": "img-fluid",
            "blockquote": "blockquote",
            "table": "table table-hover table-borderless",
            "thead": "thead-light",
            "code": "codehilite",
        }

        for el in root.iter():

            if el.tag in el_class_dict:
                BS4Treeprocessor.set_css_class(el, el_class_dict[el.tag])

        for i in range(len(self.md.htmlStash.rawHtmlBlocks)):

            bs4block = BeautifulSoup(
                self.md.htmlStash.rawHtmlBlocks[i], "html.parser"
            )

            el = bs4block.find()

            if el and el.name in el_class_dict:
                BS4Treeprocessor.set_css_class(el, el_class_dict[el.name])
                self.md.htmlStash.rawHtmlBlocks[i] = str(bs4block)

    @staticmethod
    def set_css_class(element, class_name: str):

        if isinstance(element, ElementTree.Element):

            current_class = element.attrib.get("class", "")

            if class_name not in current_class:
                new_class = f"{current_class} {class_name}".strip()
                element.set("class", new_class)

        elif isinstance(element, BeautifulSoup().new_tag("").__class__):

            if "class" not in element.attrs:
                element.attrs["class"] = []

            current_class = element["class"]

            for name in class_name.split(" "):
                if class_name not in current_class:
                    current_class.append(name)
        else:
            raise TypeError(
                "element can either be of type {}.{} or {}.{}".format(
                    BeautifulSoup().new_tag("").__class__.__module__,
                    BeautifulSoup().new_tag("").__class__.__qualname__,
                    ElementTree.Element.__module__,
                    ElementTree.Element.__qualname__,
                )
            )


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
