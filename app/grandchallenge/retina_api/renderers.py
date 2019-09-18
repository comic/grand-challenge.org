import base64

from rest_framework import renderers


class Base64Renderer(renderers.BaseRenderer):
    media_type = "image/png;base64"
    format = "base64"
    charset = "utf-8"
    render_style = "text"

    def render(self, data, media_type=None, renderer_context=None):
        return base64.b64encode(data)
