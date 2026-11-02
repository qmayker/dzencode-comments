from unittest.mock import patch

from django.test import TestCase, override_settings

from commenting.models import Comment, CommentAuthor
from events.events import Events
from events.receivers import (
    CommentAuthorSavedReceiver,
    CommentCreatedReceiver,
    CommentReplyCreatedReceiver,
    receiver_registry,
)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class CommentCreatedReceiverTests(TestCase):
    def test_comment_receivers_invalidate_their_respective_caches(self):
        author = CommentAuthor.objects.create(
            username="event-receiver-user",
            email="event-receiver@example.com",
        )
        parent = Comment.objects.create(author=author, text="Parent")
        reply = Comment.objects.create(
            author=author,
            text="Reply",
            related_comment=parent,
            target_comment=parent,
        )

        with (
            patch(
                "events.receivers.invalidate_comment_list_cache"
            ) as invalidate_comment_list,
            patch(
                "events.receivers.invalidate_comment_replies_cache"
            ) as invalidate_replies,
        ):
            CommentCreatedReceiver().handle_event({"id": reply.pk})
            CommentReplyCreatedReceiver().handle_event(
                {"id": reply.pk, "related_comment_id": parent.pk}
            )

        invalidate_comment_list.assert_called_once_with()
        invalidate_replies.assert_called_once_with(parent.pk)

    def test_author_receiver_invalidates_author_and_comment_list_caches(self):
        with (
            patch(
                "events.receivers.invalidate_comment_author_cache"
            ) as invalidate_author,
            patch(
                "events.receivers.invalidate_comment_list_cache"
            ) as invalidate_comment_list,
        ):
            CommentAuthorSavedReceiver().handle_event({"id": 42})

        invalidate_author.assert_called_once_with(42)
        invalidate_comment_list.assert_called_once_with()

    def test_comment_receiver_is_registered_for_save_events(self):
        self.assertEqual(
            [CommentCreatedReceiver],
            receiver_registry.get("comment", Events.SAVE),
        )
        self.assertEqual(
            [CommentAuthorSavedReceiver],
            receiver_registry.get("commentauthor", Events.SAVE),
        )
        self.assertEqual(
            [CommentReplyCreatedReceiver],
            receiver_registry.get("reply", Events.SAVE),
        )
