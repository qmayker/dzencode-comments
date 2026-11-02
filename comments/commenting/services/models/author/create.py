from commenting.models import CommentAuthor
from core.services import BaseModelCreateService, BaseModelService
from django.db import transaction
from events.events import Events
from events.sender import RedisEventSender

from .validation import CommentAuthorCreateValidation, CommentAuthorValidation


class CommentAuthorService(BaseModelService[CommentAuthor]):
    validator_class = CommentAuthorValidation

    def save(self, update_fields: list[str] | None = None) -> CommentAuthor:
        author = super().save(update_fields=update_fields)
        if author.pk is not None:
            transaction.on_commit(
                lambda: RedisEventSender(author, Events.SAVE).send_event(
                    {"id": author.pk}
                )
            )
        return author

    def update_home_page_url(self, new_url: str):
        self.obj.home_page = new_url
        self.save()


class CreateCommentAuthorService(
    BaseModelCreateService[CommentAuthor], CommentAuthorService
):
    model = CommentAuthor
    validator_class = CommentAuthorCreateValidation

    def __init__(self, username: str, email: str, home_page: str | None):
        obj = self.model(username=username, email=email, home_page=home_page)
        super().__init__(obj)
