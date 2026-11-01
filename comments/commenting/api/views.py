from api.authentication import CommentAuthorAuthentication
from captcha.serializers import CaptchaSerializer
from commenting.models import Comment, CommentAuthor
from commenting.services.models.author.cache import CommentAuthorCacheData
from commenting.services.models.author.operations import get_or_create
from commenting.services.models.comment.cache import CommentRepliesCacheData
from commenting.services.models.comment.create import (
    CommentCreateService,
    CommentReplyCreateService,
)
from commenting.services.models.comment.socket import WebSocketCommentEvents
from core.cache import CacheService
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from .serializers import (
    AuthorGetCreateSerializer,
    CommentCreateSerializer,
    CommentRepliesQuerySerializer,
    CommentReplySerializer,
)

type SerializedObject = dict[str, object]


class CaptchaMixin:
    request: Request

    def validate_captcha(self):
        data = self.request.POST
        serializer = CaptchaSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthorGetCreateView(CaptchaMixin, APIView):
    authentication_classes = [CommentAuthorAuthentication]

    def post(self, request: Request) -> Response:
        self.validate_captcha()
        serializer = AuthorGetCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            author = get_or_create(**serializer.validated_data)
        except DjangoValidationError as error:
            detail = (
                error.message_dict
                if hasattr(error, "message_dict")
                else {"detail": error.messages}
            )
            raise APIValidationError(detail) from error
        cache_service: CacheService[SerializedObject] = CacheService(
            CommentAuthorCacheData(kwargs={"id": author.pk})
        )
        cached_result = cache_service.get_value()
        if cached_result is None:
            cached_result = AuthorGetCreateSerializer(author).data
            cache_service.set_value(cached_result)

        token = AccessToken()
        token["author_id"] = author.pk
        token["username"] = author.username
        token["email"] = author.email
        token["home_page"] = author.home_page
        response_data = {**cached_result, "token": str(token)}
        return Response(
            response_data,
            status=status.HTTP_200_OK,
        )


class CommentCreateView(CaptchaMixin, APIView):
    # permission_classes = [IsAuthenticated]
    # authentication_classes = [CommentAuthorAuthentication]

    def post(self, request: Request) -> Response:
        self.validate_captcha()
        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        text = serializer.validated_data["text"]
        author_id = serializer.validated_data["author"].pk
        additional_file = serializer.validated_data.get("additional_file")
        target_comment = serializer.validated_data.get("target_comment")
        if target_comment is None:
            comment_service = CommentCreateService(
                text=text,
                author_id=author_id,
                additional_file=additional_file,
            )
        else:
            comment_service = CommentReplyCreateService(
                text=text,
                author_id=author_id,
                related_comment_id=serializer.validated_data["related_comment"].pk,
                target_comment_id=target_comment.pk,
                additional_file=additional_file,
            )
        comment = comment_service.create()
        response_data = CommentCreateSerializer(comment).data
        socket = WebSocketCommentEvents()
        if comment.related_comment_id is None:
            socket.broadcast_comment_created(dict(response_data))
        else:
            socket.broadcast_reply_created(comment.related_comment_id, comment.pk)
        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )


class CommentRepliesView(APIView):
    def get(self, request: Request) -> Response:
        serializer = CommentRepliesQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.validated_data["comment"]
        cache_service: CacheService[list[SerializedObject]] = CacheService(
            CommentRepliesCacheData(kwargs={"comment_id": str(comment.pk)})
        )
        cached_replies = cache_service.get_value()
        if cached_replies is not None:
            return Response(cached_replies, status=status.HTTP_200_OK)

        related_comments = CommentReplySerializer(
            Comment.objects.for_related_comment(comment).select_related(
                "author", "target_comment__author"
            ),
            many=True,
        )
        reply_data = [dict(reply) for reply in related_comments.data]
        cache_service.set_value(reply_data)
        return Response(reply_data, status=status.HTTP_200_OK)


class AuthorGetView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [CommentAuthorAuthentication]

    def get(self, request: Request):
        author: CommentAuthor = request.user
        return Response(
            AuthorGetCreateSerializer(author).data, status=status.HTTP_200_OK
        )
