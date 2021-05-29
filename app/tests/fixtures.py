from io import BytesIO

from PIL import Image as PILImage
from django.core.files.uploadedfile import InMemoryUploadedFile


def create_uploaded_image():
    io = BytesIO()
    size = (1, 1)
    color = (255, 0, 0)
    image = PILImage.new("RGB", size, color)
    image.save(io, format="JPEG")
    image_file = InMemoryUploadedFile(
        io, None, "foo.jpg", "jpeg", image.size, None
    )
    image_file.seek(0)
    return image_file
