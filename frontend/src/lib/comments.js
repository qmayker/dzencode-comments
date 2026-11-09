const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

export function normalizeComment(comment) {
  return {
    ...comment,
    replyCount: Number(comment.reply_count || 0),
    replies: [],
    pendingReplies: [],
    repliesLoaded: false,
    repliesExpanded: false,
    repliesLoading: false,
    repliesError: "",
  };
}

export function parseDate(value) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

export function formatDate(date) {
  return dateFormatter.format(date).replace(",", "");
}
