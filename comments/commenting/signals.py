from django.db.models.signals import post_delete
from django.dispatch import receiver

from commenting.models import Comment, CommentAuthor
from commenting.services.models.author.cache import invalidate_comment_author_cache
from commenting.services.models.comment.cache import (
    invalidate_comment_list_cache,
    invalidate_comment_replies_cache,
)


@receiver(post_delete, sender=Comment)
def invalidate_comment_replies(sender, instance: Comment, **kwargs) -> None:
    invalidate_comment_list_cache()
    comment_id = instance.related_comment_id or instance.pk
    if comment_id is not None:
        invalidate_comment_replies_cache(comment_id)


@receiver(post_delete, sender=CommentAuthor)
def invalidate_comment_author_on_delete(instance: CommentAuthor, **kwargs) -> None:
    if instance.pk is not None:
        invalidate_comment_author_cache(instance.pk)
    invalidate_comment_list_cache()
