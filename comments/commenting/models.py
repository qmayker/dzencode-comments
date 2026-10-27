from __future__ import annotations

from core.models import TimeStampedModel
from django.db import models

from .services.models.author.managers import CommentAuthorManager
from .services.models.comment.managers import CommentManager
from .validators import CommentTextTagsValidator, UserNameValidator


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
    text = models.TextField(max_length=2000, validators=[CommentTextTagsValidator()])

    def __str__(self):
        return f"{self.author.username} {self.text[:50]}"

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["created_at", "id"])]
