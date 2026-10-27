from django.core.exceptions import ValidationError as DjangoValidationError
from commenting.services.models.author.operations import get_or_create
from commenting.services.models.comment.create import CommentCreateService
from rest_framework import status
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AuthorGetCreateSerializer, CommentCreateSerializer


class AuthorGetCreateView(APIView):
    def post(self, request: Request) -> Response:
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
        return Response(
            AuthorGetCreateSerializer(author).data,
            status=status.HTTP_200_OK,
        )


class CommentCreateView(APIView):
    def post(self, request: Request) -> Response:
        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        comment = CommentCreateService(
            text=serializer.validated_data["text"],
            author_id=serializer.validated_data["author"].pk,
            related_comment_id=(
                serializer.validated_data["related_comment"].pk
                if serializer.validated_data.get("related_comment")
                else None
            ),
        ).create()
        return Response(
            CommentCreateSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )
