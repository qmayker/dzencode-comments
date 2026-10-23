from abc import ABC
from dataclasses import dataclass

from commenting.validators import CommentTextTagsValidator


@dataclass
class CommentValidationData:
    text: str


class CommentValidation(ABC):
    @staticmethod
    def validate_text(text: str) -> str:
        CommentTextTagsValidator()(text)
        return text

    def validate(self, data: CommentValidationData) -> None:
        self.validate_text(data.text)
