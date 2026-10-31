from commenting.enums import FileTypeEnum
from commenting.models import Comment
from core.services import BaseModelCreateService, BaseModelService
from django.core.files import File
from django.db import transaction

from .cache import invalidate_comment_list_cache, invalidate_comment_replies_cache
from .image import ImageFormatter
from .tasks import send_reply_email
from .text import CommentTextSanitizer
from .validation import CommentValidation


class CommentService(BaseModelService[Comment]):
    validator_class = CommentValidation

    def clean_text(self, text: str) -> str:
        self.text_result = CommentTextSanitizer().clean(text)
        return self.text_result.text

    def clean(self):
        self.obj.text = self.clean_text(self.obj.text)
        if self.obj.file_type == FileTypeEnum.IMG:
            self.obj.additional_file = ImageFormatter.format_image(
                self.obj.additional_file
            )

    def save(self, update_fields: list[str] | None = None) -> Comment:
        comment = super().save(update_fields=update_fields)
        invalidate_comment_list_cache()
        comment_id = comment.related_comment_id or comment.pk
        if comment_id is not None:
            invalidate_comment_replies_cache(comment_id)
        return comment


class CommentCreateService(BaseModelCreateService[Comment], CommentService):
    model = Comment

    def __init__(
        self,
        text: str,
        author_id: int,
        additional_file: File | None = None,
    ):
        obj = self.model(
            text=text,
            author_id=author_id,
            additional_file=additional_file,
        )
        super().__init__(obj)


class CommentReplyCreateService(CommentCreateService):
    def __init__(
        self,
        text: str,
        author_id: int,
        target_comment_id: int,
        related_comment_id: int | None = None,
        additional_file: File | None = None,
    ):
        obj = self.model(
            text=text,
            author_id=author_id,
            target_comment_id=target_comment_id,
            related_comment_id=related_comment_id,
            additional_file=additional_file,
        )
        CommentService.__init__(self, obj)

    def save(self, update_fields=None):
        reply_comment = super().save(update_fields)
        transaction.on_commit(lambda: send_reply_email.delay(reply_comment.pk))
        return reply_comment
