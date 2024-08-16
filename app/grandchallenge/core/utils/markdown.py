from xml.etree import ElementTree

from bs4 import BeautifulSoup
from markdown import Extension
from markdown.treeprocessors import Treeprocessor


class HtmlElementWrapper:
    def __init__(self, element):
        self.element = element

    def set_css_class(self, class_name: str):

        if isinstance(self.element, ElementTree.Element):

            current_class = self.element.attrib.get("class", "")

            if class_name not in current_class:
                new_class = f"{current_class} {class_name}".strip()
                self.element.set("class", new_class)

        elif isinstance(self.element, BeautifulSoup().new_tag("").__class__):

            if "class" not in self.element.attrs:
                self.element.attrs["class"] = []

            current_class = self.element["class"]

            for name in class_name.split(" "):
                if class_name not in current_class:
                    current_class.append(name)

    def get_element(self):
        return self.element


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
                el_wrapper = HtmlElementWrapper(el)
                el_wrapper.set_css_class(el_class_dict[el.tag])
                el = el_wrapper.get_element()

        for i in range(len(self.md.htmlStash.rawHtmlBlocks)):

            bs4block = BeautifulSoup(
                self.md.htmlStash.rawHtmlBlocks[i], "html.parser"
            )

            el = bs4block.find()

            if el and el.name in el_class_dict:
                el_wrapper = HtmlElementWrapper(el)
                el_wrapper.set_css_class(el_class_dict[el.name])
                el = el_wrapper.get_element()
                self.md.htmlStash.rawHtmlBlocks[i] = str(bs4block)


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
