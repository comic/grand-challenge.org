import re

from django.template.loader import render_to_string
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


class EmbedYoutubeExtension(Extension):
    def extendMarkdown(self, md):  # noqa: N802
        md.registerExtension(self)
        md.postprocessors.register(
            EmbedYouTubeProcessor(),
            name="embed_youtube_extension",
            priority=0,
        )


class EmbedYouTubeProcessor(Postprocessor):
    def run(self, text):
        def embed(m):
            return render_to_string(
                "partials/youtube_embed.html",
                {
                    "youtube_id": m.group(1),
                },
            )

        return re.sub(r"\[\s*youtube\s*([A-Za-z0-9_-]{11})\s*\]", embed, text)
