from markdown import Extension
from markdown.treeprocessors import Treeprocessor


class BS4Extension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.registerExtension(self)
        md.treeprocessors.register(BS4Treeprocessor(md), "bs4_extension", 0)


class BS4Treeprocessor(Treeprocessor):
    def run(self, root):
        for el in root.iter():
            if el.tag == "img":
                el.set("class", "img-fluid")

            elif el.tag == "blockquote":
                el.set("class", "blockquote")

            elif el.tag == "table":
                el.set("class", "table table-hover table-borderless")

            elif el.tag == "thead":
                el.set("class", "thead-light")
