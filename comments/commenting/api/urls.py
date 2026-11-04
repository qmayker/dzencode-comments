from django.urls import path

from .views import (
    AuthorGetCreateView,
    AuthorGetView,
    CaptchaVerifyView,
    CommentCreateView,
    CommentRepliesView,
)

app_name = "commenting_api"

urlpatterns = [
    path("captcha/verify/", CaptchaVerifyView.as_view(), name="captcha-verify"),
    path("authors/", AuthorGetCreateView.as_view(), name="author-get-create"),
    path("comments/", CommentCreateView.as_view(), name="comment-create"),
    path("comments/replies/", CommentRepliesView.as_view(), name="comment-replies"),
    path("get-author/", AuthorGetView.as_view(), name="author-get"),
]
