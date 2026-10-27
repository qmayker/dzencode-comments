from commenting.models import Comment
from core.services import BaseModelCreateService, BaseModelService

from .text import CommentTextSanitizer
from .validation import CommentValidation


class CommentService(BaseModelService[Comment]):
    validator_class = CommentValidation

    def clean_text(self, text: str) -> str:
        self.text_result = CommentTextSanitizer().clean(text)
        return self.text_result.text

    def clean(self):
        self.obj.text = self.clean_text(self.obj.text)


class CommentCreateService(BaseModelCreateService[Comment], CommentService):
    model = Comment

    def __init__(
        self,
        text: str,
        author_id: int,
        target_comment_id: int | None = None,
        related_comment_id: int | None = None,
    ):
        obj = self.model(
            text=text,
            author_id=author_id,
            target_comment_id=target_comment_id,
            related_comment_id=related_comment_id,
        )
        super().__init__(obj)
