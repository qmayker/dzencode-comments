from commenting.models import CommentAuthor
from core.validators import BaseValidator
from django.core.exceptions import ValidationError


class CommentAuthorValidation(BaseValidator[CommentAuthor]):
    def validate(self) -> None:
        self.obj.full_clean()


class CommentAuthorCreateValidation(CommentAuthorValidation):
    @staticmethod
    def validate_email_unique(username: str, email: str):
        username_obj = CommentAuthor.objects.filter(username=username).exists()
        if username_obj:
            raise ValidationError("Это имя пользователя уже занято.")
        email_obj = CommentAuthor.objects.filter(email=email).exists()
        if email_obj:
            raise ValidationError("Этот адрес электронной почты уже используется.")

    def validate(self):
        super().validate()
        self.validate_email_unique(self.obj.username, self.obj.email)
