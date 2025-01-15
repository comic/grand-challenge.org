from bs4 import BeautifulSoup
from markdown import Extension
from markdown.postprocessors import Postprocessor
from markdown.treeprocessors import Treeprocessor


class BS4Extension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.postprocessors.register(BS4Postprocessor(md), "bs4_extension", 0)


class BS4Postprocessor(Postprocessor):
    def run(self, text):
        soup = BeautifulSoup(text, "html.parser")

        class_map = {
            "img": ["border shadow img-fluid"],
            "blockquote": ["blockquote"],
            "table": ["table", "table-hover", "table-borderless"],
            "thead": ["thead-light"],
            "code": ["codehilite"],
        }

        for element in soup.find_all([*class_map.keys()]):
            classes = element.get("class", [])
            for new_class in class_map[element.name]:
                if new_class not in classes:
                    classes.append(new_class)
            element["class"] = classes

        return str(soup)


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
