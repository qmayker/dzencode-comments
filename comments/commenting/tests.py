from django.core.exceptions import ValidationError
from django.test import TestCase

from commenting.models import Comment, CommentAuthor
from commenting.services.models.comment.create import (
    CommentCreateService,
    CommentService,
)


class CommentServiceTests(TestCase):
    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="test-author",
            email="test@example.com",
            home_page="https://example.com",
        )

    def test_comment_service_validates_before_saving(self):
        comment = Comment(
            author=self.author,
            text="<strong>unclosed",
        )

        with self.assertRaises(ValidationError):
            CommentService(comment).save()

        self.assertIsNone(comment.pk)
        self.assertEqual(Comment.objects.count(), 0)

    def test_create_service_uses_comment_service_and_returns_saved_comment(self):
        service = CommentCreateService(
            text="<span>comment text</span>",
            author_id=self.author.pk,
        )

        comment = service.create()

        self.assertIsInstance(service, CommentService)
        self.assertEqual(comment, service.obj)
        self.assertIsNotNone(comment.pk)
        self.assertEqual(comment.text, "comment text")


class CommentListViewTests(TestCase):
    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="list-author",
            email="list@example.com",
        )
        Comment.objects.bulk_create(
            [
                Comment(author=self.author, text=f"Comment {number}")
                for number in range(26)
            ]
        )

    def test_comment_list_displays_25_comments_per_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 25)
        self.assertContains(response, "Наступна")

    def test_comment_list_shows_remaining_comment_on_second_page(self):
        response = self.client.get("/", {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 1)
        self.assertContains(response, "Comment 0")
