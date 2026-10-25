from commenting.models import Comment
from core.validators import BaseValidator


class CommentValidation(BaseValidator[Comment]):
    def validate(self) -> None:
        self.obj.full_clean()
