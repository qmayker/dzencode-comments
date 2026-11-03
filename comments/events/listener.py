import json
import logging
from typing import TypedDict

import redis

from .events import Events
from .receivers import CommentCreatedReceiver, CommentReplyCreatedReceiver  # noqa: F401
from .registry import ReceiverRegistry

logger = logging.getLogger("comments")


class EventData(TypedDict):
    event: Events
    model_name: str
    data: dict[str, object]


class RedisEventListener:
    def __init__(
        self, redis_client: redis.Redis, list_name: str, registry: ReceiverRegistry
    ) -> None:
        self.redis_client = redis_client
        self.list_name = list_name
        self.registry = registry
        self._running = False

    def listen(self) -> None:
        self._running = True
        while self._running:
            item = self.redis_client.blpop(self.list_name, timeout=1)
            if item is None:
                continue
            _, value = item
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            data = json.loads(value)
            data["event"] = Events(data["event"])
            event_data: EventData = data
            receiver_classes = self.registry.get(
                event_data["model_name"],
                event_data["event"],
            )
            for receiver_class in receiver_classes:
                logger.debug(
                    "Dispatching event %s to receiver %s",
                    event_data,
                    receiver_class.__name__,
                )
                receiver_class().handle_event(event_data["data"])

    def stop(self) -> None:
        self._running = False
