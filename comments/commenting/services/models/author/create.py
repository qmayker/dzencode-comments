from commenting.models import CommentAuthor
from core.services import BaseModelCreateService, BaseModelService

from .validation import CommentAuthorCreateValidation, CommentAuthorValidation


class CommentAuthorService(BaseModelService[CommentAuthor]):
    validator_class = CommentAuthorValidation

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
