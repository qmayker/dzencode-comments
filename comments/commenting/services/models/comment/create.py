from commenting.models import Comment

from .text import CommentTextSanitizer
from .validation import CommentValidation, CommentValidationData


class BaseCommentService:
    model = Comment

    def __init__(self, obj: Comment):
        self.obj = obj
        self.data = CommentValidationData(text=self.obj.text)

    def get_text(self, text: str) -> str:
        self.text_result = CommentTextSanitizer().clean(text)
        return self.text_result.text

    def save(self) -> Comment:
        self.obj.text = self.get_text(self.data.text)
        self.obj.save()
        return self.obj


class CommentMixin(BaseCommentService, CommentValidation): ...


class CommentService(CommentMixin):
    def save(self):
        self.validate(self.data)
        return super().save()


class CommentCreateService(CommentMixin):
    def __init__(
        self, text: str, author_id: int, related_comment_id: int | None = None
    ):
        obj = self.model(
            text=text,
            author_id=author_id,
            related_comment_id=related_comment_id,
        )
        super().__init__(obj)

    def create(self):
        self.validate(self.data)
        return self.save()
