from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image as PILImage


def create_uploaded_image(*, width=1, height=1, name="foo.jpg"):
    io = BytesIO()
    size = (width, height)
    color = (255, 0, 0)
    image = PILImage.new("RGB", size, color)
    image.save(io, format="JPEG")
    image_file = InMemoryUploadedFile(io, None, name, "jpeg", image.size, None)
    image_file.seek(0)
    return image_file
