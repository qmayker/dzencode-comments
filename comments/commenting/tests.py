from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status

from commenting.models import Comment, CommentAuthor
from commenting.services.models.author.create import (
    CommentAuthorService,
    CreateCommentAuthorService,
)
from commenting.services.models.author.operations import get_or_create
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

    def test_comment_create_service_validates_before_saving(self):
        service = CommentCreateService(
            text="<strong>unclosed",
            author_id=self.author.pk,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertIsNone(service.obj.pk)
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
        self.assertIsNone(comment.related_comment_id)

    def test_create_service_links_reply_to_related_comment(self):
        parent = Comment.objects.create(author=self.author, text="Parent comment")
        service = CommentCreateService(
            text="Reply text",
            author_id=self.author.pk,
            related_comment_id=parent.pk,
        )

        reply = service.create()

        self.assertEqual(reply.related_comment, parent)
        self.assertIn(reply, parent.replies.all())

    def test_create_service_rejects_nonexistent_related_comment(self):
        service = CommentCreateService(
            text="Reply text",
            author_id=self.author.pk,
            related_comment_id=999,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertIsNone(service.obj.pk)
        self.assertEqual(Comment.objects.count(), 0)


class CommentQuerySetTests(TestCase):
    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="queryset-author",
            email="queryset@example.com",
        )
        self.main_comment = Comment.objects.create(
            author=self.author,
            text="Main comment",
        )
        self.reply = Comment.objects.create(
            author=self.author,
            text="Reply",
            related_comment=self.main_comment,
        )
        self.other_main_comment = Comment.objects.create(
            author=self.author,
            text="Another main comment",
        )

    def test_main_comments_returns_only_comments_without_related_comment(self):
        self.assertQuerySetEqual(
            Comment.objects.main_comments(),
            [self.other_main_comment, self.main_comment],
        )

    def test_for_related_comment_returns_replies_to_the_selected_comment(self):
        self.assertQuerySetEqual(
            Comment.objects.for_related_comment(self.main_comment),
            [self.reply],
        )

    def test_for_related_comment_accepts_comment_id(self):
        self.assertQuerySetEqual(
            Comment.objects.for_related_comment(self.main_comment.pk),
            [self.reply],
        )


class CommentCreateApiTests(TestCase):
    url = "/api/commenting/comments/"

    def test_author_response_can_be_used_to_create_comment(self):
        author_response = self.client.post(
            "/api/commenting/authors/",
            data={
                "username": "flowuser",
                "email": "flow@example.com",
            },
            content_type="application/json",
        )
        self.assertEqual(
            author_response.status_code,
            status.HTTP_200_OK,
            author_response.data,
        )

        response = self.client.post(
            self.url,
            data={
                "author": author_response.data["id"],
                "text": "Created through the API flow",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Comment.objects.get().text, "Created through the API flow")

    def test_post_creates_comment_for_author(self):
        author = CommentAuthor.objects.create(
            username="apiuser",
            email="api@example.com",
        )

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "API comment",
                "related_comment": None,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["author"], author.pk)
        self.assertEqual(Comment.objects.get().text, "API comment")

    def test_post_creates_reply_with_related_comment(self):
        author = CommentAuthor.objects.create(
            username="replyuser",
            email="reply@example.com",
        )
        parent = Comment.objects.create(author=author, text="Parent comment")

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Reply comment",
                "related_comment": parent.pk,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            Comment.objects.get(pk=response.data["id"]).related_comment,
            parent,
        )


class CommentAuthorServiceTests(TestCase):
    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="existingauthor",
            email="existing@example.com",
            home_page="https://old.example.com",
        )

    def test_create_service_validates_and_saves_author(self):
        service = CreateCommentAuthorService(
            username="newauthor",
            email="new@example.com",
            home_page="https://example.com",
        )

        author = service.create()

        self.assertEqual(author, service.obj)
        self.assertIsNotNone(author.pk)
        self.assertEqual(author.username, "newauthor")
        self.assertEqual(CommentAuthor.objects.count(), 2)

    def test_create_service_rejects_duplicate_username(self):
        service = CreateCommentAuthorService(
            username=self.author.username,
            email="another@example.com",
            home_page=None,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertIsNone(service.obj.pk)
        self.assertEqual(CommentAuthor.objects.count(), 1)

    def test_create_service_rejects_duplicate_email(self):
        service = CreateCommentAuthorService(
            username="anotherauthor",
            email=self.author.email,
            home_page=None,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertIsNone(service.obj.pk)
        self.assertEqual(CommentAuthor.objects.count(), 1)

    def test_update_home_page_url_saves_author(self):
        service = CommentAuthorService(self.author)

        service.update_home_page_url("https://new.example.com")

        self.author.refresh_from_db()
        self.assertEqual(self.author.home_page, "https://new.example.com")

    def test_get_or_create_creates_author_when_missing(self):
        author = get_or_create(
            username="newauthor",
            email="new@example.com",
            home_page="https://example.com",
        )

        self.assertEqual(author.username, "newauthor")
        self.assertEqual(author.email, "new@example.com")
        self.assertEqual(CommentAuthor.objects.count(), 2)

    def test_get_or_create_returns_existing_author_and_updates_home_page(self):
        author = get_or_create(
            username=self.author.username,
            email=self.author.email,
            home_page="https://new.example.com",
        )

        self.author.refresh_from_db()
        self.assertEqual(author.pk, self.author.pk)
        self.assertEqual(self.author.home_page, "https://new.example.com")
        self.assertEqual(CommentAuthor.objects.count(), 1)

    def test_get_or_create_without_home_page_preserves_existing_url(self):
        author = get_or_create(
            username=self.author.username,
            email=self.author.email,
        )

        self.author.refresh_from_db()
        self.assertEqual(author.pk, self.author.pk)
        self.assertEqual(self.author.home_page, "https://old.example.com")


class AuthorGetCreateApiTests(TestCase):
    url = "/api/commenting/authors/"

    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="existingauthor",
            email="existing@example.com",
        )

    def test_post_returns_validation_error_for_email_used_by_another_author(self):
        response = self.client.post(
            self.url,
            data={
                "username": "differentauthor",
                "email": self.author.email,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(CommentAuthor.objects.count(), 1)

    def test_post_returns_validation_error_for_username_used_by_another_author(self):
        response = self.client.post(
            self.url,
            data={
                "username": self.author.username,
                "email": "different@example.com",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertEqual(CommentAuthor.objects.count(), 1)


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
        self.assertContains(response, 'id="comment-create-form"')
        self.assertContains(response, "Наступна")

    def test_comment_create_form_is_displayed_before_sort_form(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertLess(
            content.index('id="comment-create-form"'),
            content.index('class="sort-form"'),
        )

    def test_reply_form_is_rendered_once_inside_hidden_storage(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count('id="comment-reply-form"'), 1)
        self.assertIn(
            '<div id="comment-reply-storage" hidden>',
            content,
        )
        self.assertIn('id="reply_username"', content)

    def test_forms_do_not_include_a_relation_input(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "related_comment_id")
        self.assertNotContains(response, 'name="related_comment"')

    def test_each_comment_element_includes_its_id_as_data_attribute(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        for comment in response.context["comment_list"]:
            with self.subTest(comment_id=comment.id):
                self.assertContains(
                    response,
                    f'data-comment-id="{comment.id}"',
                )

    def test_each_comment_has_a_reply_button(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(
            content.count('class="comment-reply-button"'),
            len(response.context["comment_list"]),
        )
        self.assertContains(response, "Відповісти")

    def test_comment_list_shows_remaining_comment_on_second_page(self):
        response = self.client.get("/", {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 1)
        self.assertContains(response, "Comment 0")
