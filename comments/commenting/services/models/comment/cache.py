from dataclasses import dataclass
from typing import ClassVar

from core.cache import CacheData
from django.core.cache import cache


@dataclass
class CommentRepliesCacheData(CacheData):
    prefix: str = "comment:replies"
    expiration_time: int = 60 * 60


@dataclass
class CommentListCacheData(CacheData):
    prefix: str = "comment:list"
    expiration_time: int = 60 * 60
    version_key: ClassVar[str] = "comment:list:version"


def invalidate_comment_list_cache() -> None:
    version_key = CommentListCacheData.version_key
    if not cache.add(version_key, 1, timeout=None):
        cache.incr(version_key)


def invalidate_comment_replies_cache(comment_id: int) -> None:
    cache_data = CommentRepliesCacheData(
        kwargs={"comment_id": str(comment_id)}
    )
    cache.delete(cache_data.get_key())
