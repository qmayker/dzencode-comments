from dataclasses import dataclass
from typing import Self

from django.conf import settings


@dataclass
class FileFormatData:
    all_formats: set[str]
    image_formats: set[str]
    file_formats: set[str]

    @classmethod
    def get_all_formats(cls) -> Self:
        image_formats = {
            extension.lower().lstrip(".") for extension in settings.IMAGE_FORMATS
        }
        file_formats = {"txt"}

        return cls(
            all_formats=image_formats | file_formats,
            image_formats=image_formats,
            file_formats=file_formats,
        )
