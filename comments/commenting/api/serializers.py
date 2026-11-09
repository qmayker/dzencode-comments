from captcha.serializers import CaptchaSerializer
from commenting.models import Comment, CommentAuthor
from commenting.validators import UserNameValidator
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer


class AuthorGetCreateSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(validators=[UserNameValidator()])
    email = serializers.EmailField()
    home_page = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CommentAuthor
        fields = ["id", "username", "email", "home_page"]


class CommentCreateSerializer(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_home_page = serializers.URLField(
        source="author.home_page",
        read_only=True,
        allow_null=True,
    )
    target_comment_username = serializers.CharField(
        source="target_comment.author.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "related_comment",
            "target_comment",
            "text",
            "author",
            "additional_file",
            "file_type",
            "author_username",
            "author_home_page",
            "target_comment_username",
        ]

    def validate(self, attrs):
        related_comment = attrs.get("related_comment")
        target_comment = attrs.get("target_comment")
        if related_comment is None and target_comment is None:
            return attrs
        if related_comment is None or target_comment is None:
            raise serializers.ValidationError(
                {
                    "related_comment": (
                        "Это поле необходимо указать вместе с полем target_comment."
                    )
                }
            )

        expected_related_id = target_comment.related_comment_id or target_comment.pk
        if related_comment.pk != expected_related_id:
            raise serializers.ValidationError(
                {
                    "related_comment": (
                        "Укажите корневой комментарий ветки ответа."
                    )
                }
            )
        return attrs


class CommentReplySerializer(ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_home_page = serializers.URLField(
        source="author.home_page",
        read_only=True,
        allow_null=True,
    )
    target_comment_username = serializers.CharField(
        source="target_comment.author.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "related_comment",
            "target_comment",
            "text",
            "author",
            "additional_file",
            "file_type",
            "author_username",
            "author_home_page",
            "target_comment_username",
            "created_at",
        ]


class CommentRepliesQuerySerializer(serializers.Serializer):
    comment_id = serializers.PrimaryKeyRelatedField(
        source="comment",
        queryset=Comment.objects.all(),
    )


class CaptchaValidateSerializer(CaptchaSerializer):
    methods = serializers.CharField(write_only=True)

    def validate_methods(self, value: str) -> list[str]:
        methods = [method.strip() for method in value.split(";") if method.strip()]
        if not methods:
            raise serializers.ValidationError("Необходимо указать хотя бы один метод.")
        return methods
