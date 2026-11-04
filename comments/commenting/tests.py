from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
from rest_framework import status

from commenting.enums import FileTypeEnum
from commenting.models import Comment, CommentAuthor
from commenting.services.models.author.create import (
    CommentAuthorService,
    CreateCommentAuthorService,
)
from commenting.services.models.author.operations import get_or_create
from commenting.services.models.comment.create import (
    CommentCreateService,
    CommentReplyCreateService,
    CommentService,
)
from commenting.services.models.comment.managers import CommentQuerySet
from commenting.services.models.comment.socket.types import CommentsGroup
from commenting.services.models.comment.validation import CommentValidation
from commenting.validators import FileFormatData
from events.events import EventCustomModel, Events
from events.receivers import CommentCreatedReceiver, CommentReplyCreatedReceiver


def create_png_upload(filename):
    image_data = BytesIO()
    Image.new("RGB", (1, 1)).save(image_data, format="PNG")
    return SimpleUploadedFile(filename, image_data.getvalue(), content_type="image/png")


class CommentFileValidationTests(TestCase):
    def test_accepts_configured_image_extensions_case_insensitively(self):
        for filename in ("image.jpg", "image.GIF", "image.PnG"):
            with self.subTest(filename=filename):
                comment = Comment(additional_file=create_png_upload(filename))
                CommentValidation(comment).validate_file()

    def test_file_formats_default_to_txt(self):
        formats = FileFormatData(
            all_formats=set(),
            image_formats=set(),
            file_formats={"txt"},
        )

        self.assertEqual(formats.file_formats, {"txt"})

    def test_get_all_formats_uses_default_file_formats(self):
        formats = FileFormatData.get_all_formats()

        self.assertEqual(formats.file_formats, {"txt"})
        self.assertEqual(
            formats.all_formats,
            formats.image_formats | formats.file_formats,
        )

    def test_comment_get_suffix_sets_image_file_type(self):
        comment = Comment(additional_file=create_png_upload("IMAGE.PNG"))

        self.assertEqual(comment.get_suffix(), "png")
        self.assertEqual(comment.file_type, FileTypeEnum.IMG)

    def test_comment_get_suffix_sets_text_file_type(self):
        comment = Comment(additional_file=SimpleUploadedFile("notes.TXT", b"notes"))

        self.assertEqual(comment.get_suffix(), "txt")
        self.assertEqual(comment.file_type, FileTypeEnum.TXT)

    def test_comment_get_suffix_clears_file_type_when_file_is_missing(self):
        comment = Comment(file_type=FileTypeEnum.IMG)

        self.assertIsNone(comment.get_suffix())
        self.assertIsNone(comment.file_type)

    def test_comment_form_file_input_accepts_all_supported_formats(self):
        from commenting.forms import CommentCreateForm

        accept = CommentCreateForm().fields["additional_file"].widget.attrs["accept"]

        self.assertEqual(accept, ".gif,.jpg,.png,.txt")

    def test_rejects_extensions_not_in_image_formats_or_txt(self):
        with self.assertRaises(ValidationError):
            CommentValidation(
                Comment(additional_file=SimpleUploadedFile("document.pdf", b"document"))
            ).validate_file()

    def test_accepts_txt_files_within_size_limit(self):
        CommentValidation(
            Comment(additional_file=SimpleUploadedFile("document.txt", b"text"))
        ).validate_file()

    def test_rejects_txt_files_over_size_limit(self):
        oversized_file = SimpleUploadedFile(
            "document.txt",
            b"x" * (100 * 1024 + 1),
        )

        with self.assertRaises(ValidationError):
            CommentValidation(
                Comment(additional_file=oversized_file)
            ).validate_file()


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
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
        self.assertIsNone(comment.target_comment_id)

    @patch("commenting.services.models.comment.create.RedisEventSender")
    def test_save_sends_save_event_after_commit(self, event_sender_class):
        service = CommentCreateService(
            text="Comment text",
            author_id=self.author.pk,
        )

        with self.captureOnCommitCallbacks(execute=True):
            comment = service.create()

        event_sender_class.assert_called_once_with(comment, Events.SAVE)
        event_sender_class.return_value.send_event.assert_called_once_with(
            {"id": comment.pk, "related_comment_id": None}
        )

    @patch("commenting.services.models.comment.create.RedisEventSender")
    def test_save_sends_reply_event_with_reply_model_name(self, event_sender_class):
        parent = Comment.objects.create(author=self.author, text="Parent comment")
        service = CommentReplyCreateService(
            text="Reply text",
            author_id=self.author.pk,
            target_comment_id=parent.pk,
            related_comment_id=parent.pk,
        )

        with self.captureOnCommitCallbacks(execute=True):
            reply = service.create()

        event_sender_class.assert_called_once_with(EventCustomModel.REPLY, Events.SAVE)
        event_sender_class.return_value.send_event.assert_called_once_with(
            {"id": reply.pk, "related_comment_id": parent.pk}
        )

    def test_create_service_sets_target_and_related_comment_for_main_reply(self):
        parent = Comment.objects.create(author=self.author, text="Parent comment")
        service = CommentReplyCreateService(
            text="Reply text",
            author_id=self.author.pk,
            target_comment_id=parent.pk,
            related_comment_id=parent.pk,
        )

        reply = service.create()

        self.assertEqual(reply.related_comment, parent)
        self.assertEqual(reply.target_comment, parent)
        self.assertIn(reply, parent.replies.all())

    def test_create_service_keeps_reply_in_root_thread_and_targets_reply(self):
        parent = Comment.objects.create(author=self.author, text="Parent comment")
        first_reply = Comment.objects.create(
            author=self.author,
            text="First reply",
            related_comment=parent,
            target_comment=parent,
        )
        service = CommentReplyCreateService(
            text="Reply to first reply",
            author_id=self.author.pk,
            target_comment_id=first_reply.pk,
            related_comment_id=parent.pk,
        )

        reply = service.create()

        self.assertEqual(reply.related_comment, parent)
        self.assertEqual(reply.target_comment, first_reply)
        self.assertIn(reply, parent.replies.all())

    def test_create_service_rejects_nonexistent_target_comment(self):
        service = CommentReplyCreateService(
            text="Reply text",
            author_id=self.author.pk,
            target_comment_id=999,
            related_comment_id=999,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertIsNone(service.obj.pk)
        self.assertEqual(Comment.objects.count(), 0)

    def test_create_service_rejects_related_comment_that_is_not_thread_root(self):
        parent = Comment.objects.create(author=self.author, text="Parent comment")
        target = Comment.objects.create(
            author=self.author,
            text="First reply",
            related_comment=parent,
            target_comment=parent,
        )
        service = CommentReplyCreateService(
            text="Invalid reply",
            author_id=self.author.pk,
            target_comment_id=target.pk,
            related_comment_id=target.pk,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertEqual(Comment.objects.count(), 2)

    def test_create_service_requires_related_comment_when_target_is_set(self):
        target = Comment.objects.create(author=self.author, text="Target comment")
        service = CommentReplyCreateService(
            text="Reply without thread root",
            author_id=self.author.pk,
            target_comment_id=target.pk,
        )

        with self.assertRaises(ValidationError):
            service.create()

        self.assertEqual(Comment.objects.count(), 1)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
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
            target_comment=self.main_comment,
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


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
)
class CommentCreateApiTests(TestCase):
    url = "/api/commenting/comments/"

    def captcha_payload(self):
        from django.core.cache import cache

        token = "valid-test-token"
        cache.set(
            f"captcha_pass:{token}", ["author_get_create", "comment_create"], 300
        )
        return {"captcha_token": token}

    def test_author_response_can_be_used_to_create_comment(self):
        from rest_framework_simplejwt.tokens import AccessToken

        author_response = self.client.post(
            "/api/commenting/authors/",
            data={
                "username": "flowuser",
                "email": "flow@example.com",
                **self.captcha_payload(),
            },
            content_type="application/json",
        )
        self.assertEqual(
            author_response.status_code,
            status.HTTP_200_OK,
            author_response.data,
        )
        author = CommentAuthor.objects.get(pk=author_response.data["id"])
        token = AccessToken(author_response.data["token"])
        self.assertEqual(token["author_id"], author.pk)
        self.assertEqual(token["username"], author.username)
        self.assertEqual(token["email"], author.email)
        self.assertEqual(token["home_page"], author.home_page)

        author_details = self.client.get(
            "/api/commenting/get-author/",
            HTTP_AUTHORIZATION=f"Bearer {author_response.data['token']}",
        )
        self.assertEqual(author_details.status_code, status.HTTP_200_OK)
        self.assertEqual(author_details.data["id"], author.pk)
        self.assertEqual(author_details.data["username"], author.username)
        self.assertEqual(author_details.data["email"], author.email)
        self.assertEqual(author_details.data["home_page"], author.home_page)

        response = self.client.post(
            self.url,
            data={
                "author": author_response.data["id"],
                "text": "Created through the API flow",
                **self.captcha_payload(),
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
                "target_comment": None,
                **self.captcha_payload(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["author"], author.pk)
        self.assertIsNone(response.data["related_comment"])
        self.assertIsNone(response.data["target_comment"])
        self.assertEqual(Comment.objects.get().text, "API comment")

    def test_post_rejects_invalid_captcha_without_creating_comment(self):
        author = CommentAuthor.objects.create(
            username="invalid-captcha-user",
            email="invalid-captcha@example.com",
        )
        captcha = self.captcha_payload()
        captcha["captcha_token"] = "invalid"

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Should not be created",
                **captcha,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("captcha_token", response.data)
        self.assertEqual(Comment.objects.count(), 0)

    @patch("commenting.api.views.WebSocketCommentEvents")
    def test_post_broadcasts_comment_to_page_room(self, socket_events):
        author = CommentAuthor.objects.create(
            username="socket-user",
            email="socket@example.com",
        )

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Live comment",
                **self.captcha_payload(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        socket_events.return_value.broadcast_comment_created.assert_called_once()
        (comment_data,) = (
            socket_events.return_value.broadcast_comment_created.call_args.args
        )
        self.assertEqual(comment_data["id"], response.data["id"])
        self.assertEqual(comment_data["text"], "Live comment")

    def test_post_saves_uploaded_file_under_configured_upload_path(self):
        author = CommentAuthor.objects.create(
            username="file-upload-user",
            email="file-upload@example.com",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    self.url,
                    data={
                        "author": author.pk,
                        "text": "Comment with attachment",
                        "additional_file": create_png_upload("attachment.png"),
                        **self.captcha_payload(),
                    },
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_201_CREATED,
                    response.data,
                )
                comment = Comment.objects.get(pk=response.data["id"])
                self.assertEqual(response.data["file_type"], FileTypeEnum.IMG)
                self.assertTrue(response.data["additional_file"].startswith("/media/"))
                self.assertTrue(comment.additional_file.name.startswith("comments/"))
                self.assertTrue(
                    Path(media_root, comment.additional_file.name).is_file()
                )

    def test_post_returns_text_file_type_for_uploaded_text_file(self):
        author = CommentAuthor.objects.create(
            username="text-file-upload-user",
            email="text-file-upload@example.com",
        )

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Comment with text attachment",
                "additional_file": SimpleUploadedFile("notes.txt", b"Notes"),
                **self.captcha_payload(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["file_type"], FileTypeEnum.TXT)

    @patch("commenting.api.views.WebSocketCommentEvents")
    def test_post_broadcasts_reply_for_reply_count(
        self,
        socket_events,
    ):
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
                "target_comment": parent.pk,
                **self.captcha_payload(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reply = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(reply.related_comment, parent)
        self.assertEqual(reply.target_comment, parent)
        socket_events.return_value.broadcast_comment_created.assert_not_called()
        socket_events.return_value.broadcast_reply_created.assert_called_once_with(
            parent.pk,
            reply.pk,
        )

    def test_post_creates_reply_to_reply_in_the_same_parent_thread(self):
        author = CommentAuthor.objects.create(
            username="nested-reply-user",
            email="nested-reply@example.com",
        )
        parent = Comment.objects.create(author=author, text="Parent comment")
        target = Comment.objects.create(
            author=author,
            text="First reply",
            related_comment=parent,
            target_comment=parent,
        )

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Reply to first reply",
                "related_comment": parent.pk,
                "target_comment": target.pk,
                **self.captcha_payload(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reply = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(reply.related_comment, parent)
        self.assertEqual(reply.target_comment, target)

    def test_post_rejects_related_comment_that_is_not_target_thread_root(self):
        author = CommentAuthor.objects.create(
            username="invalid-thread-user",
            email="invalid-thread@example.com",
        )
        parent = Comment.objects.create(author=author, text="Parent comment")
        target = Comment.objects.create(
            author=author,
            text="First reply",
            related_comment=parent,
            target_comment=parent,
        )

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Invalid reply",
                "related_comment": target.pk,
                "target_comment": target.pk,
                **self.captcha_payload(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("related_comment", response.data)

    def test_post_requires_related_comment_when_target_is_set(self):
        author = CommentAuthor.objects.create(
            username="missing-related-user",
            email="missing-related@example.com",
        )
        target = Comment.objects.create(author=author, text="Target comment")

        response = self.client.post(
            self.url,
            data={
                "author": author.pk,
                "text": "Reply without thread root",
                "target_comment": target.pk,
                **self.captcha_payload(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("related_comment", response.data)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class CommentRepliesApiTests(TestCase):
    url = "/api/commenting/comments/replies/"

    def setUp(self):
        self.author = CommentAuthor.objects.create(
            username="replies-api-author",
            email="replies-api@example.com",
        )
        self.comment = Comment.objects.create(
            author=self.author,
            text="Main comment",
        )
        self.reply = Comment.objects.create(
            author=self.author,
            related_comment=self.comment,
            target_comment=self.comment,
            text="Reply",
        )
        self.unrelated_comment = Comment.objects.create(
            author=self.author,
            text="Another main comment",
        )
        Comment.objects.create(
            author=self.author,
            related_comment=self.unrelated_comment,
            text="Unrelated reply",
        )

    def test_get_returns_serialized_replies_for_comment_id(self):
        response = self.client.get(self.url, {"comment_id": self.comment.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.reply.pk)
        self.assertEqual(response.data[0]["related_comment"], self.comment.pk)
        self.assertEqual(response.data[0]["target_comment"], self.comment.pk)
        self.assertEqual(response.data[0]["text"], "Reply")
        self.assertEqual(response.data[0]["author"], self.author.pk)
        self.assertEqual(response.data[0]["author_username"], self.author.username)
        self.assertEqual(
            response.data[0]["target_comment_username"],
            self.author.username,
        )
        self.assertTrue(response.data[0]["created_at"])

    def test_get_uses_cached_reply_data(self):
        self.client.get(self.url, {"comment_id": self.comment.pk})

        with patch.object(
            Comment.objects,
            "for_related_comment",
            side_effect=AssertionError("Replies should be read from cache"),
        ):
            response = self.client.get(self.url, {"comment_id": self.comment.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.reply.pk)

    def test_new_reply_invalidates_cached_reply_data(self):
        self.client.get(self.url, {"comment_id": self.comment.pk})
        new_reply = CommentReplyCreateService(
            author_id=self.author.pk,
            related_comment_id=self.comment.pk,
            target_comment_id=self.comment.pk,
            text="New reply",
        ).create()
        CommentReplyCreatedReceiver().handle_event(
            {
                "id": new_reply.pk,
                "related_comment_id": self.comment.pk,
            }
        )

        response = self.client.get(self.url, {"comment_id": self.comment.pk})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn(new_reply.pk, [reply["id"] for reply in response.data])

    def test_get_returns_bad_request_when_comment_id_is_missing(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment_id", response.data)

    def test_get_returns_bad_request_when_comment_id_does_not_exist(self):
        response = self.client.get(self.url, {"comment_id": 999})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment_id", response.data)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
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

    @patch("commenting.services.models.author.create.RedisEventSender")
    def test_create_service_sends_author_save_event(self, event_sender_class):
        service = CreateCommentAuthorService(
            username="cachedauthor",
            email="cached@example.com",
            home_page=None,
        )

        with self.captureOnCommitCallbacks(execute=True):
            author = service.create()

        event_sender_class.assert_called_once_with(author, Events.SAVE)
        event_sender_class.return_value.send_event.assert_called_once_with(
            {"id": author.pk}
        )

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

    @patch("commenting.services.models.author.create.RedisEventSender")
    def test_update_home_page_url_saves_author(self, event_sender_class):
        service = CommentAuthorService(self.author)

        with self.captureOnCommitCallbacks(execute=True):
            service.update_home_page_url("https://new.example.com")

        self.author.refresh_from_db()
        self.assertEqual(self.author.home_page, "https://new.example.com")
        event_sender_class.assert_called_once_with(self.author, Events.SAVE)
        event_sender_class.return_value.send_event.assert_called_once_with(
            {"id": self.author.pk}
        )

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

    def captcha_payload(self):
        from django.core.cache import cache

        token = "valid-test-token"
        cache.set(
            f"captcha_pass:{token}", ["author_get_create", "comment_create"], 300
        )
        return {"captcha_token": token}

    def test_post_returns_validation_error_for_email_used_by_another_author(self):
        response = self.client.post(
            self.url,
            data={
                "username": "differentauthor",
                "email": self.author.email,
                **self.captcha_payload(),
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
                **self.captcha_payload(),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertEqual(CommentAuthor.objects.count(), 1)

    def test_post_rejects_invalid_captcha_without_creating_author(self):
        captcha = self.captcha_payload()
        captcha["captcha_token"] = "invalid"

        response = self.client.post(
            self.url,
            data={
                "username": "invalidcaptcha",
                "email": "invalid-captcha@example.com",
                **captcha,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("captcha_token", response.data)
        self.assertEqual(CommentAuthor.objects.count(), 1)

    def test_author_post_removes_only_used_method_from_captcha_token(self):
        captcha = self.captcha_payload()
        data = {"username": "newauthor", "email": "new@example.com", **captcha}

        response = self.client.post(
            self.url, data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        from django.core.cache import cache

        self.assertEqual(
            cache.get("captcha_pass:valid-test-token"), ["comment_create"]
        )

        repeat = self.client.post(self.url, data=data, content_type="application/json")
        self.assertEqual(repeat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("captcha_token", repeat.data)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class CaptchaVerifyApiTests(TestCase):
    url = "/api/commenting/captcha/verify/"

    def test_valid_captcha_returns_token(self):
        from captcha.models import CaptchaStore

        hashkey = CaptchaStore.generate_key()
        response = self.client.post(
            self.url,
            data={
                "captcha_code": CaptchaStore.objects.get(hashkey=hashkey).response,
                "captcha_hashkey": hashkey,
                "methods": "author_get_create; comment_create;",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        from django.core.cache import cache

        token = response.data["captcha_token"]
        self.assertEqual(
            cache.get(f"captcha_pass:{token}"), ["author_get_create", "comment_create"]
        )

    def test_missing_methods_is_rejected(self):
        from captcha.models import CaptchaStore

        hashkey = CaptchaStore.generate_key()
        response = self.client.post(
            self.url,
            data={
                "captcha_code": CaptchaStore.objects.get(hashkey=hashkey).response,
                "captcha_hashkey": hashkey,
                "methods": " ; ",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("methods", response.data)

    def test_token_is_rejected_for_method_not_in_list(self):
        from django.core.cache import cache

        cache.set("captcha_pass:only-author", ["author_get_create"], 300)
        response = self.client.post(
            "/api/commenting/comments/",
            data={"author": 1, "text": "x", "captcha_token": "only-author"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("captcha_token", response.data)

    def test_invalid_captcha_is_rejected(self):
        from captcha.models import CaptchaStore

        hashkey = CaptchaStore.generate_key()
        response = self.client.post(
            self.url,
            data={
                "captcha_code": "invalid",
                "captcha_hashkey": hashkey,
                "methods": "comment_create",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("captcha_token", response.data)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }
)
class CommentWebSocketTests(SimpleTestCase):
    def test_receives_new_comment_from_shared_room(self):
        from commenting.services.models.comment.socket.routing import (
            websocket_urlpatterns,
        )

        async def receive_comment():
            communicator = WebsocketCommunicator(
                URLRouter(websocket_urlpatterns),
                "/ws/comments/",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            comment_data = {"id": 42, "text": "Live comment"}
            await get_channel_layer().group_send(
                CommentsGroup().room_name,
                {
                    "type": "comment_created",
                    "comment": comment_data,
                },
            )
            message = await communicator.receive_json_from()
            self.assertEqual(
                message,
                {"type": "comment.created", "comment": comment_data},
            )
            reply_event = {
                "related_comment_id": 42,
                "reply_id": 43,
            }
            await get_channel_layer().group_send(
                CommentsGroup().room_name,
                {
                    "type": "reply_created",
                    "comment": reply_event,
                },
            )
            reply_message = await communicator.receive_json_from()
            self.assertEqual(
                reply_message,
                {"type": "reply.created", "comment": reply_event},
            )
            await communicator.disconnect()

        async_to_sync(receive_comment)()


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class CommentListViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.author = CommentAuthor.objects.create(
            username="list-author",
            email="list@example.com",
        )
        Comment.objects.bulk_create(
            [
                Comment(
                    author=self.author,
                    text=f"Pagination test comment {number}",
                )
                for number in range(26)
            ]
        )

    def test_comment_list_displays_25_comments_per_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 25)
        self.assertContains(response, 'id="comment-create-form"')
        self.assertContains(response, 'id="new-comments-container"')
        self.assertContains(response, "Переглянути нові коментарі (0)")
        self.assertContains(response, "Наступна")

    def test_comment_list_uses_cached_models(self):
        self.client.get("/")

        original_fetch_all = CommentQuerySet._fetch_all

        def fail_if_queryset_is_not_cached(queryset):
            if queryset._result_cache is None:
                raise AssertionError("Page models should be read from cache")
            return original_fetch_all(queryset)

        with patch.object(
            CommentQuerySet,
            "_fetch_all",
            fail_if_queryset_is_not_cached,
        ):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 25)

    def test_each_page_uses_its_own_cached_models(self):
        first_page = self.client.get("/")
        second_page = self.client.get("/", {"page": 2})

        original_fetch_all = CommentQuerySet._fetch_all

        def fail_if_queryset_is_not_cached(queryset):
            if queryset._result_cache is None:
                raise AssertionError("Page models should be read from cache")
            return original_fetch_all(queryset)

        with patch.object(
            CommentQuerySet,
            "_fetch_all",
            fail_if_queryset_is_not_cached,
        ):
            cached_first_page = self.client.get("/")
            cached_second_page = self.client.get("/", {"page": 2})

        self.assertEqual(
            [comment.pk for comment in cached_first_page.context["comment_list"]],
            [comment.pk for comment in first_page.context["comment_list"]],
        )
        self.assertEqual(
            [comment.pk for comment in cached_second_page.context["comment_list"]],
            [comment.pk for comment in second_page.context["comment_list"]],
        )
        self.assertEqual(len(cached_first_page.context["comment_list"]), 25)
        self.assertEqual(len(cached_second_page.context["comment_list"]), 1)

    def test_new_comment_invalidates_cached_models(self):
        self.client.get("/")
        new_comment = CommentCreateService(
            author_id=self.author.pk,
            text="New main comment",
        ).create()
        CommentCreatedReceiver().handle_event(
            {"id": new_comment.pk, "related_comment_id": None}
        )

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["comment_list"][0].pk,
            new_comment.pk,
        )

    def test_sort_order_uses_separate_cached_models(self):
        response = self.client.get(
            "/",
            {"field": "username", "orderingType": "asc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 25)

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
        self.assertContains(response, "window.authorGetUrl")
        self.assertEqual(content.count('id="comment-reply-form"'), 1)
        self.assertIn(
            '<div id="comment-reply-storage" hidden>',
            content,
        )
        self.assertIn('id="reply_username"', content)

    def test_comment_forms_include_captcha_fields(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count('name="captcha_0"'), 2)
        self.assertEqual(content.count('name="captcha_1"'), 2)
        self.assertEqual(content.count('class="js-captcha-refresh"'), 2)
        self.assertContains(response, "js/captcha.js")

        refresh_response = self.client.get(
            "/captcha/refresh/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn("image_url", refresh_response.json())
        self.assertIn("key", refresh_response.json())

    def test_comment_forms_include_html_tag_toolbar(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        for tag in ("i", "strong", "code", "a"):
            self.assertEqual(content.count(f'data-tag="{tag}"'), 2)
        self.assertContains(response, "js/tags.js")

    def test_text_file_dialog_is_available_for_comment_attachments(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="text-file-dialog"')
        self.assertContains(response, "js/txt.js")

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
        self.assertNotContains(response, "Переглянути відповіді")

    def test_replies_button_is_rendered_only_for_comments_with_replies(self):
        parent = Comment.objects.first()
        target = CommentReplyCreateService(
            author_id=self.author.pk,
            text="First reply",
            related_comment_id=parent.pk,
            target_comment_id=parent.pk,
        ).create()
        CommentReplyCreateService(
            author_id=self.author.pk,
            text="Reply to first reply",
            related_comment_id=parent.pk,
            target_comment_id=target.pk,
        ).create()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-comment-id="{parent.pk}"')
        self.assertContains(response, 'class="comment-view-replies-button"')
        self.assertContains(response, "Переглянути відповіді (2)")
        self.assertNotContains(response, "comment-replies-status")
        self.assertNotContains(response, "Reply to first reply")
        self.assertContains(response, "window.commentRepliesUrl")

    def test_comment_list_shows_remaining_comment_on_second_page(self):
        response = self.client.get("/", {"page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["comment_list"]), 1)
        self.assertContains(response, "Pagination test comment 0")
