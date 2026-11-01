from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path("ws/comments/$", consumers.CommentConsumer.as_asgi())
]
