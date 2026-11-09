from html import unescape
import re

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


class CommentTextTagsValidator:
    def validate_text(self, text: str) -> bool:
        return bool(unescape(strip_tags(text)).strip())

    def validate_tags(self, text: str) -> bool:
        stack = []
        pattern = r"<(/?)([a-zA-Z][\w:-]*)\b[^>]*>"

        for match in re.finditer(pattern, text):
            closing, tag_name = match.groups()
            tag = match.group(0)

            if tag.rstrip().endswith("/>"):
                continue

            if closing:
                if not stack or stack[-1] != tag_name:
                    return False
                stack.pop()
            else:
                stack.append(tag_name)
        return len(stack) == 0

    def __call__(self, value: str) -> str:
        if not self.validate_text(value):
            raise ValidationError("Комментарий не может быть пустым.")

        is_valid = self.validate_tags(value)
        if is_valid:
            return
        raise ValidationError("Теги закрыты некорректно.")

    def deconstruct(self):
        return (
            f"{self.__class__.__module__}.{self.__class__.__qualname__}",
            (),
            {},
        )
