from commenting.enums import FileTypeEnum
from commenting.models import Comment
from commenting.validators import FileFormatData
from core.validators import BaseValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


class CommentValidation(BaseValidator[Comment]):
    def validate(self) -> None:
        self.validate_file()
        self.obj.full_clean()
        self.validate_comments(
            self.obj.related_comment_id,
            self.obj.target_comment_id,
        )

    def validate_file(self) -> None:
        suffix = self.obj.get_suffix()
        if suffix is None:
            return

        formats = FileFormatData.get_all_formats()
        if suffix not in formats.all_formats:
            raise ValidationError(
                {"additional_file": "Формат файла не поддерживается."}
            )

        if self.obj.file_type == FileTypeEnum.TXT:
            size = self.obj.additional_file.size / 1024
            if size > settings.TXT_FILE_SIZE:
                raise ValidationError(
                    {"additional_file": "Размер файла слишком велик."}
                )
        elif self.obj.file_type == FileTypeEnum.IMG:
            try:
                image = Image.open(self.obj.additional_file)
                image.verify()
            except (UnidentifiedImageError, OSError) as error:
                raise ValidationError(
                    {"additional_file": "Изображение повреждено или имеет неверный формат."}
                ) from error

    def validate_comments(self, related_id: int | None, target_id: int | None):
        if related_id is None and target_id is None:
            return
        if related_id is None or target_id is None:
            raise ValidationError(
                "Необходимо указать идентификаторы связанного комментария и ответа."
            )
        target_comment = self.obj.target_comment
        if related_id == target_id:
            if target_comment.related_comment_id is not None:
                raise ValidationError(
                    "В этом случае ответ должен относиться к основному комментарию."
                )
            return

        related_comment = self.obj.related_comment
        if (
            related_comment.related_comment_id is not None
            or target_comment.related_comment_id != related_id
        ):
            raise ValidationError(
                "Ответ должен относиться к ветке указанного основного комментария."
            )
