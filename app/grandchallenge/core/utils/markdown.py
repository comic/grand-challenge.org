from bs4 import BeautifulSoup
from markdown import Extension
from markdown.postprocessors import Postprocessor
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

            elif el.tag == "code":
                el.set("class", "codehilite")


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


class HtmlTagsExtension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.registerExtension(self)
        md.postprocessors.register(
            HtmlTagsPostprocessor(md), "htmltags_extension", 35
        )


class HtmlTagsPostprocessor(Postprocessor):
    def run(self, lines):
        for i in range(len(self.md.htmlStash.rawHtmlBlocks)):
            bs4block = BeautifulSoup(
                self.md.htmlStash.rawHtmlBlocks[i], "html.parser"
            )
            img = bs4block.find("img")
            if img:
                if "class" not in img.attrs:
                    img.attrs["class"] = []

                if "img-fluid" not in img.attrs["class"]:
                    img["class"].append("img-fluid")

                self.md.htmlStash.rawHtmlBlocks[i] = str(bs4block)
        return lines
