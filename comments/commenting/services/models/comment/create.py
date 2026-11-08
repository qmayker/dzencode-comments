from html import unescape

from commenting.enums import FileTypeEnum
from commenting.models import Comment
from core.services import BaseModelCreateService, BaseModelService
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction
from django.utils.html import strip_tags
from events.events import EventCustomModel, Events
from events.sender import RedisEventSender

from .image import ImageFormatter
from .text import CommentTextSanitizer
from .validation import CommentValidation


class CommentService(BaseModelService[Comment]):
    validator_class = CommentValidation

    def clean_text(self, text: str) -> str:
        self.text_result = CommentTextSanitizer().clean(text)
        cleaned_text = self.text_result.text
        if not unescape(strip_tags(cleaned_text)).strip():
            raise ValidationError({"text": "Comment cannot be blank."})
        return cleaned_text

    def clean(self):
        self.obj.text = self.clean_text(self.obj.text)
        if self.obj.file_type == FileTypeEnum.IMG:
            self.obj.additional_file = ImageFormatter.format_image(
                self.obj.additional_file
            )

    def save_model(self, update_fields: list[str] | None = None) -> Comment:
        return super().save(update_fields=update_fields)

    def save(self, update_fields: list[str] | None = None) -> Comment:
        comment = self.save_model(update_fields)
        transaction.on_commit(
            lambda: RedisEventSender(comment, Events.SAVE).send_event(
                {"id": comment.pk, "related_comment_id": None}
            )
        )
        return comment


class CommentReplyService(CommentService):
    def save(self, update_fields: list[str] | None = None) -> Comment:
        reply = self.save_model(update_fields)
        transaction.on_commit(
            lambda: RedisEventSender(
                EventCustomModel.REPLY,
                Events.SAVE,
            ).send_event(
                {
                    "id": reply.pk,
                    "related_comment_id": reply.related_comment_id,
                }
            )
        )
        return reply


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


class CommentReplyCreateService(BaseModelCreateService[Comment], CommentReplyService):
    model = Comment

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
        super().__init__(obj)

    def save(self, update_fields=None):
        return super().save(update_fields)
