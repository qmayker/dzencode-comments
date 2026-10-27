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

    class Meta:
        model = Comment
        fields = ["id", "related_comment", "text", "author"]


class CommentRepliesQuerySerializer(serializers.Serializer):
    comment_id = serializers.PrimaryKeyRelatedField(
        source="comment",
        queryset=Comment.objects.all(),
    )
