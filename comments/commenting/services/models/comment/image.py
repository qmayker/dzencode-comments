from io import BytesIO

from django.core.files import File
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError


class ImageFormatter:
    MAX_WIDTH = 320
    MAX_HEIGHT = 240

    @classmethod
    def format_image(cls, image_file: File):
        image_file.seek(0)
        image = Image.open(image_file)
        try:
            image.thumbnail((cls.MAX_WIDTH, cls.MAX_HEIGHT))
        except (UnidentifiedImageError, OSError):
            raise ValueError("Can`t thumbnail image")
        saved_image = BytesIO()
        image.save(saved_image, format=image.format)
        return ContentFile(
            saved_image.getvalue(),
            name=image_file.name,
        )
