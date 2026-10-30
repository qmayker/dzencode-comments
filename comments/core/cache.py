from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache


@dataclass
class CacheData:
    prefix: str
    expiration_time: int
    kwargs: dict[str, str] = field(default_factory=dict)

    def get_key(self):
        cache_key = self.prefix
        for key, value in self.kwargs.items():
            cache_key = f"{cache_key}:{key}:{value}"
        return cache_key


class CacheService[V: Any]:
    def __init__(self, data: CacheData):
        self.data = data

    def get_value(self) -> V | None:
        return cache.get(self.data.get_key())

    def set_value(self, value: V):
        cache.set(self.data.get_key(), value, self.data.expiration_time)

    def delete(self):
        cache.delete(self.data.get_key())
