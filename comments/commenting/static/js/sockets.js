document.addEventListener("DOMContentLoaded", () => {
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

    if (!message.comment) {
      return;
    }

    const eventNames = {
      "comment.created": "comment-created",
      "reply.created": "reply-created",
    };
    const eventName = eventNames[message.type];
    if (!eventName) {
      return;
    }

    window.dispatchEvent(
      new CustomEvent(eventName, { detail: message.comment }),
    );
  });

  socket.addEventListener("error", (error) => {
    console.error("Comment WebSocket connection failed.", error);
  });

  window.commentSocket = socket;
});
