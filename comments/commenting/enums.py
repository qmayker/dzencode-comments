from django.db.models import TextChoices


class FileTypeEnum(TextChoices):
    TXT = "text"
    IMG = "image"