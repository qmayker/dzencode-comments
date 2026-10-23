from django.test import TestCase

from commenting.models import Comment, CommentAuthor
from commenting.services.models.comment.create import (
    BaseCommentService,
    CommentCreateService,
)


class CommentServiceTests(TestCase):
    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="test-author",
            email="test@example.com",
            home_page="https://example.com",
        )

    def test_base_service_saves_without_validation(self):
        comment = Comment(
            author=self.author,
            text="<strong>unclosed",
        )

        saved_comment = BaseCommentService(comment).save()

        self.assertIsNotNone(saved_comment.pk)
        self.assertEqual(Comment.objects.count(), 1)

    def test_create_service_uses_base_service_and_returns_saved_comment(self):
        service = CommentCreateService(
            text="<span>comment text</span>",
            author_id=self.author.pk,
        )

        comment = service.create()

        self.assertIsInstance(service, BaseCommentService)
        self.assertEqual(comment, service.obj)
        self.assertIsNotNone(comment.pk)
        self.assertEqual(comment.text, "comment text")
