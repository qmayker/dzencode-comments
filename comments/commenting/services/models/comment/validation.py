from commenting.models import Comment
from core.validators import BaseValidator
from django.core.exceptions import ValidationError


class CommentValidation(BaseValidator[Comment]):
    def validate(self) -> None:
        self.obj.full_clean()
        self.validate_comments(
            self.obj.related_comment_id,
            self.obj.target_comment_id,
        )

    def validate_comments(self, related_id: int | None, target_id: int | None):
        if related_id is None and target_id is None:
            return
        if related_id is None or target_id is None:
            raise ValidationError("Related and target comment IDs must both be set.")

        target_comment = self.obj.target_comment
        if related_id == target_id:
            if target_comment.related_comment_id is not None:
                raise ValidationError(
                    "A reply target must be a main comment in this case."
                )
            return

        related_comment = self.obj.related_comment
        if (
            related_comment.related_comment_id is not None
            or target_comment.related_comment_id != related_id
        ):
            raise ValidationError(
                "Target comment must be a reply under the related main comment."
            )
