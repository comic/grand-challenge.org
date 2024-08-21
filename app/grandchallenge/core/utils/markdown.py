from xml.etree import ElementTree

from bs4 import BeautifulSoup, Tag
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
                self.set_css_class(
                    element=el, class_name=el_class_dict[el.tag]
                )

        for i, html_block in enumerate(self.md.htmlStash.rawHtmlBlocks):

            bs4block = BeautifulSoup(html_block, "html.parser")

            for tag, tag_class in el_class_dict.items():
                for el in bs4block.find_all(tag):
                    self.set_css_class(element=el, class_name=tag_class)
                    self.md.htmlStash.rawHtmlBlocks[i] = str(bs4block)

    @staticmethod
    def set_css_class(*, element, class_name):

        if isinstance(element, ElementTree.Element):

            current_class = element.attrib.get("class", "")

            if class_name not in current_class:
                new_class = f"{current_class} {class_name}".strip()
                element.set("class", new_class)

        elif isinstance(element, Tag):

            if "class" not in element.attrs:
                element.attrs["class"] = []

            current_class = element["class"]

            for name in class_name.split(" "):
                if class_name not in current_class:
                    current_class.append(name)
        else:
            raise TypeError("Unsupported element")


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
