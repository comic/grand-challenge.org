from xml.etree import ElementTree

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor
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


class EmbedYoutubeExtension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.registerExtension(self)
        md.inlinePatterns.register(
            EmbedYouTubeInLineProcessor(
                r"^\[\s*youtube\s*([A-Za-z0-9_-]{11})\s*([0-9]*)\s*([0-9]*)\s*\]",
                md,
            ),
            "embed_youtube_extension",
            0,
        )


class EmbedYouTubeInLineProcessor(InlineProcessor):
    def handleMatch(self, m, data):  # noqa: N802
        youtube_id = m.group(1)

        el = ElementTree.Element("iframe")

        el.set(
            "src",
            f"https://www.youtube-nocookie.com/embed/{youtube_id}?"
            "disablekb=1&"  # Prevents keyboard shortcuts
            "rel=0&",  # Disables related videos from other channels
        )
        el.set(
            "allow",
            "; ".join(
                [
                    "accelerometer",
                    "autoplay",
                    "encrypted-media",
                    "gyroscope",
                    "picture-in-picture",
                    "web-share",
                    "fullscreen",
                ]
            ),
        )
        el.set(
            "class",
            " ".join(
                [
                    "embed-responsive",
                    "embed-responsive-16by9",
                    "rounded",
                ]
            ),
        )

        el.set("frameborder", "0")

        el.set("loading", "lazy")

        el.set(
            "sandbox",
            " ".join(
                [
                    "allow-scripts",
                    "allow-same-origin",
                    "allow-presentation",
                    "allow-popups",
                ]
            ),
        )

        return el, m.start(0), m.end(0)
