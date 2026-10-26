from __future__ import annotations

from typing import TYPE_CHECKING, Self

from django.db import models

from .types import AuthorData

if TYPE_CHECKING:
    from commenting.models import CommentAuthor


class CommentAuthorQuerySet(models.QuerySet["CommentAuthor"]):
    def filter_author(self, author_data: AuthorData) -> Self:
        return self.filter(email=author_data.email, username=author_data.username)

    def get_author(self, author_data: AuthorData) -> CommentAuthor | None:
        return self.filter_author(author_data=author_data).first()


class CommentAuthorManager(models.Manager.from_queryset(CommentAuthorQuerySet)):
    pass
