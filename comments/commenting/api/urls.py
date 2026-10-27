from django.urls import path

from .views import AuthorGetCreateView, CommentCreateView

app_name = "commenting_api"

urlpatterns = [
    path("authors/", AuthorGetCreateView.as_view(), name="author-get-create"),
    path("comments/", CommentCreateView.as_view(), name="comment-create"),
]
