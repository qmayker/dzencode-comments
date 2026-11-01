from asgiref.sync import async_to_sync
from channels.layers import BaseChannelLayer, get_channel_layer

from .types import CommentsGroup


class CommentEventEnum:
    CREATED = "comment_created"
    REPLY_CREATED = "reply_created"


type CommentData = dict[str, object]


class WebSocketCommentEvents:
    def __init__(self, group: CommentsGroup | None = None):
        self.channel_layer = self._get_channel_layer()
        if group is None:
            group = CommentsGroup()
        self.group = group

    def _get_channel_layer(self) -> BaseChannelLayer:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            raise RuntimeError("No channel layer is configured.")
        return channel_layer

    def send_event(self, comment_data: CommentData, event_type: CommentEventEnum):
        async_to_sync(self.channel_layer.group_send)(
            self.group.room_name,
            {
                "type": event_type,
                "comment": comment_data,
            },
        )

    def broadcast_comment_created(
        self,
        comment_data: CommentData,
    ) -> None:
        self.send_event(comment_data, event_type=CommentEventEnum.CREATED)

    def broadcast_reply_created(
        self,
        related_comment_id: int,
        reply_id: int,
    ) -> None:
        self.send_event(
            {
                "related_comment_id": related_comment_id,
                "reply_id": reply_id,
            },
            event_type=CommentEventEnum.REPLY_CREATED,
        )
