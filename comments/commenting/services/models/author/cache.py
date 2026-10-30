from dataclasses import dataclass

from core.cache import CacheData, CacheService


@dataclass
class CommentAuthorCacheData(CacheData):
    prefix: str = "comment:author"
    expiration_time: int = 60 * 60 * 24


def invalidate_comment_author_cache(author_id: int) -> None:
    cache_service: CacheService[dict[str, object]] = CacheService(
        CommentAuthorCacheData(kwargs={"id": str(author_id)})
    )
    cache_service.delete()
