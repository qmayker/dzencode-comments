from commenting.models import CommentAuthor
from core.services import BaseModelCreateService, BaseModelService

from ..comment.cache import invalidate_comment_list_cache
from .cache import invalidate_comment_author_cache
from .validation import CommentAuthorCreateValidation, CommentAuthorValidation


class CommentAuthorService(BaseModelService[CommentAuthor]):
    validator_class = CommentAuthorValidation

    def save(self, update_fields: list[str] | None = None) -> CommentAuthor:
        author = super().save(update_fields=update_fields)
        if author.pk is not None:
            invalidate_comment_author_cache(author.pk)
        invalidate_comment_list_cache()
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
