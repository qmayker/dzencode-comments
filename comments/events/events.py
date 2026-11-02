from enum import StrEnum


class Events(StrEnum):
    SAVE = "save"
    CREATE = "create"


class EventCustomModel(StrEnum):
    REPLY = "reply"
