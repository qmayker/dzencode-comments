import re

from django.core.exceptions import ValidationError


class CommentTextTagsValidator:
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
        is_valid = self.validate_tags(value)
        if is_valid:
            return
        raise ValidationError("Tags are not closed properly")
