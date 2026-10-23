from dataclasses import dataclass

import nh3


@dataclass
class SanitizeResult:
    text: str
    changed: bool


class CommentTextSanitizer:
    def __init__(self):
        self.cleaner = nh3.Cleaner(
            tags={"a", "code", "i", "strong"},
            attributes={"a": {"href", "title"}},
        )

    def clean(self, value: str) -> SanitizeResult:
        cleaned = self.cleaner.clean(value)
        normalized = value.replace("\r\n", "\n").replace("\r", "\n")

        return SanitizeResult(
            text=cleaned,
            changed=cleaned != normalized,
        )
