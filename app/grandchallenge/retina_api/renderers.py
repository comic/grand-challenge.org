import base64

from rest_framework import renderers


class Base64Renderer(renderers.BaseRenderer):
    """A renderer that converts a bytes object into a base64 encoded png."""

    media_type = "image/png;base64"
    format = "base64"
    charset = "utf-8"
    render_style = "text"

    def render(self, data, media_type=None, renderer_context=None):
        # Only encode to base64 if data is a bytes object, otherwise an exception
        # has occured and it returns a dict containing the error.
        if isinstance(data, bytes):
            return base64.b64encode(data)
        return data
