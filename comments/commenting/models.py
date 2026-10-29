from __future__ import annotations

from pathlib import Path

from core.models import TimeStampedModel
from django.db import models

from .enums import FileTypeEnum
from .services.models.author.managers import CommentAuthorManager
from .services.models.comment.managers import CommentManager
from .validators import CommentTextTagsValidator, FileFormatData, UserNameValidator


class CommentAuthor(TimeStampedModel):
    objects = CommentAuthorManager()

    username = models.CharField(
        max_length=100,
        validators=[UserNameValidator()],
        unique=True,
    )
    email = models.EmailField(unique=True)
    home_page = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.username}"


class Comment(TimeStampedModel):
    objects = CommentManager()

    author = models.ForeignKey(
        CommentAuthor, on_delete=models.CASCADE, related_name="comments"
    )
    related_comment = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE
    )
    target_comment = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="directed_replies",
        on_delete=models.CASCADE,
    )
    text = models.TextField(max_length=2000, validators=[CommentTextTagsValidator()])
    additional_file = models.FileField(
        upload_to="comments/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    file_type = models.CharField(
        choices=FileTypeEnum.choices, blank=True, null=True, default=None
    )

    def __str__(self):
        return f"{self.author.username} {self.text[:50]}"

    def get_suffix(self) -> str | None:
        if not self.additional_file:
            self.file_type = None
            return None

        suffix = Path(self.additional_file.name).suffix.lstrip(".").lower()
        formats = FileFormatData.get_all_formats()
        if suffix in formats.image_formats:
            self.file_type = FileTypeEnum.IMG
        elif suffix in formats.file_formats:
            self.file_type = FileTypeEnum.TXT
        else:
            self.file_type = None
        return suffix

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["created_at", "id"])]
