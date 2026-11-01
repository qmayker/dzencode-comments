from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .types import CommentsGroup


class CommentConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self) -> None:
        self.group = CommentsGroup()
        self.group_name = self.group.room_name
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: object, **kwargs: object) -> None:
        await self.close(code=1008)

    async def comment_created(self, event: dict[str, object]) -> None:
        await self.send_json(
            {
                "type": "comment.created",
                "comment": event["comment"],
            }
        )

    async def reply_created(self, event: dict[str, object]) -> None:
        await self.send_json(
            {
                "type": "reply.created",
                "comment": event["comment"],
            }
        )
