from __future__ import annotations

from typing import TYPE_CHECKING

from .events import Events

if TYPE_CHECKING:
    from .receivers import EventReceiver


class ReceiverRegistry:
    def __init__(self) -> None:
        self._receivers: dict[str, dict[Events, list[type[EventReceiver]]]] = {}

    def register(self, event: Events, receiver: type[EventReceiver]) -> None:
        if not isinstance(event, Events):
            raise TypeError("event must be an Events value.")
        event_name = receiver.get_event_name()
        if not isinstance(event_name, str) or not event_name:
            raise TypeError("receiver.model_name must be a non-empty string.")

        model_events = self._receivers.setdefault(event_name, {})
        model_events.setdefault(event, []).append(receiver)

    def get(self, event_name: str, event: Events) -> list[type[EventReceiver]]:
        if not isinstance(event_name, str) or not event_name:
            raise TypeError("model_name must be a non-empty string.")
        if not isinstance(event, Events):
            raise TypeError("event must be an Events value.")
        return list(self._receivers.get(event_name, {}).get(event, ()))
