from __future__ import annotations

from typing import TYPE_CHECKING, Self

from django.db import models

if TYPE_CHECKING:
    from commenting.models import Comment


class CommentQuerySet(models.QuerySet["Comment"]):
    def main_comments(self) -> Self:
        return self.filter(related_comment__isnull=True)

    def for_related_comment(self, related_comment: Comment | int) -> Self:
        return self.filter(related_comment=related_comment)


class CommentManager(models.Manager.from_queryset(CommentQuerySet)):
    pass
