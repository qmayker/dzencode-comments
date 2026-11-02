import json

import redis
from core.models import get_model_name
from django.conf import settings
from django.db.models import Model

from .events import EventCustomModel, Events
from .listener import EventData


class RedisEventSender:
    def __init__(
        self,
        model: Model | type[Model] | EventCustomModel,
        event_type: Events,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self.model = model
        self.event_type = event_type
        if redis_client is None:
            redis_client = redis.Redis.from_url(settings.EVENTS_REDIS_URL)
        self.redis_client = redis_client
        self.list_name = settings.EVENTS_REDIS_KEY

    def send_event(self, data: dict[str, object]) -> None:
        model_name = (
            self.model.value
            if isinstance(self.model, EventCustomModel)
            else get_model_name(self.model)
        )
        event_data: EventData = {
            "event": self.event_type,
            "model_name": model_name,
            "data": data,
        }
        self.redis_client.rpush(
            self.list_name,
            json.dumps(event_data, ensure_ascii=False),
        )
