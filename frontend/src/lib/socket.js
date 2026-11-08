const EVENT_HANDLERS = {
  "comment.created": "onCommentCreated",
  "reply.created": "onReplyCreated",
};

export function connectCommentSocket(handlers) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(
    `${protocol}//${window.location.host}/ws/comments/`,
  );

  socket.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      console.error("Could not parse WebSocket message.", error);
      return;
    }

    const handlerName = EVENT_HANDLERS[message.type];
    if (message.comment && handlerName) {
      handlers[handlerName]?.(message.comment);
    }
  });

  socket.addEventListener("error", (error) => {
    console.error("Comment WebSocket connection failed.", error);
  });

  return socket;
}
