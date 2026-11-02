from __future__ import annotations

from abc import ABCMeta, abstractmethod
from inspect import isabstract
from typing import ClassVar

from commenting.models import Comment, CommentAuthor
from commenting.services.models.author.cache import invalidate_comment_author_cache
from commenting.services.models.comment.cache import (
    invalidate_comment_list_cache,
    invalidate_comment_replies_cache,
)
from core.models import get_model_name
from django.db.models import Model

from .events import EventCustomModel, Events
from .registry import ReceiverRegistry

receiver_registry = ReceiverRegistry()


class EventReceiverMeta(ABCMeta):
    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwargs: object,
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)

        if isabstract(cls) or name == "EventReceiver":
            return

        event_type = getattr(cls, "event_type", None)
        model = getattr(cls, "model", None)
        if not isinstance(event_type, Events):
            raise TypeError(f"{name}.event_type must be an Events value.")
        if not isinstance(model, type) or not issubclass(model, Model):
            raise TypeError(f"{name}.model must be a Django model class.")
        event_name = cls.get_event_name()
        if not isinstance(event_name, str) or not event_name:
            raise TypeError(f"{name}.model_name must be a non-empty string.")
        cls.event_name = event_name
        receiver_registry.register(event_type, cls)


class EventReceiver(metaclass=EventReceiverMeta):
    event_type: ClassVar[Events]
    model: ClassVar[type[Model]]
    event_name: ClassVar[str | None] = None

    @classmethod
    def get_event_name(cls) -> str:
        if cls.event_name is not None:
            return cls.event_name
        return get_model_name(cls.model)

    @classmethod
    def get_event(cls) -> str:
        return f"{cls.get_event_name()}.{cls.event_type}"

    @abstractmethod
    def handle_event(self, event: object) -> None:
        raise NotImplementedError


class CommentCreatedReceiver(EventReceiver):
    event_type = Events.SAVE
    model = Comment

    def handle_event(self, event: object) -> None:
        invalidate_comment_list_cache()


class CommentAuthorSavedReceiver(EventReceiver):
    event_type = Events.SAVE
    model = CommentAuthor

    def handle_event(self, event: object) -> None:
        if not isinstance(event, dict):
            raise TypeError("Comment author event data must be a dictionary.")

        author_id = event.get("id")
        if not isinstance(author_id, int):
            raise ValueError("Comment author event data must contain an integer id.")

        invalidate_comment_author_cache(author_id)
        invalidate_comment_list_cache()


class CommentReplyCreatedReceiver(EventReceiver):
    event_type = Events.SAVE
    model = Comment
    event_name = EventCustomModel.REPLY.value

    def handle_event(self, event: object) -> None:
        if not isinstance(event, dict):
            raise TypeError("Comment reply event data must be a dictionary.")

        related_comment_id = event.get("related_comment_id")
        if not isinstance(related_comment_id, int):
            raise ValueError(
                "Comment reply event data must contain an integer related_comment_id."
            )

        invalidate_comment_replies_cache(related_comment_id)
