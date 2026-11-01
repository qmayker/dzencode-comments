from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class CommentsGroup:
    page: int = field(default=1)
    prefix: ClassVar[str] = "comments"

    @property
    def room_name(self):
        return f"comments_{self.page}"
