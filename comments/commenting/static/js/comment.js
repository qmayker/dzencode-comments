async function postJson(url, data) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": Cookies.get("csrftoken")
        },
        body: JSON.stringify(data),
    });
    // console.log("Status:", response.status);
    // console.log("Response:", await response.text());
    const responseData = await response.json();

    if (!response.ok) {
        const message = Object.values(responseData)
        .flat()
        .join(" ");
        throw new Error(message || `API request failed (${response.status}).`);
    }

    return responseData;
}

async function createComment({
  authorUrl,
  commentUrl,
  username,
  email,
  homePage,
  text,
  captchaCode,
  captchaHashkey,
  targetCommentId = null,
  relatedCommentId = null,
}) {
  const author = await postJson(authorUrl, {
    username,
    email,
    home_page: homePage || null,
  });

  return postJson(commentUrl, {
    author: author.id,
    text,
    target_comment: targetCommentId,
    related_comment: relatedCommentId,
    captcha_code: captchaCode,
    captcha_hashkey: captchaHashkey,
  });
}

window.createComment = createComment;

async function getCommentReplies(url, commentId) {
  const requestUrl = new URL(url, window.location.href);
  requestUrl.searchParams.set("comment_id", commentId);

  const response = await fetch(requestUrl);
  const responseData = await response.json();

  if (!response.ok) {
    const message = Object.values(responseData)
      .flat()
      .join(" ");
    throw new Error(message || `API request failed (${response.status}).`);
  }

  return responseData;
}

const commentDateFormatter = new Intl.DateTimeFormat("uk-UA", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function buildCommentElement(comment, { isReply }) {
  const article = document.createElement("article");
  article.className = isReply ? "comment comment-reply" : "comment";
  article.dataset.commentId = comment.id;

  const header = document.createElement("header");
  header.className = "comment-header";
  const author = document.createElement("strong");
  author.className = "comment-author";
  author.textContent = comment.author_username;
  const date = document.createElement("time");
  date.className = "comment-date";
  const createdAt = new Date(comment.created_at);
  if (!Number.isNaN(createdAt.getTime())) {
    date.dateTime = createdAt.toISOString();
    date.textContent = commentDateFormatter.format(createdAt).replace(",", "");
  }
  header.append(author, date);
  article.append(header);

  if (
    isReply &&
    comment.target_comment !== comment.related_comment &&
    comment.target_comment_username
  ) {
    const target = document.createElement("p");
    target.className = "reply-target";
    target.textContent = `У відповідь на коментар ${comment.target_comment_username}`;
    article.append(target);
  }

  const body = document.createElement("div");
  body.className = "comment-body";
  body.innerHTML = comment.text;
  article.append(body);

  const actions = document.createElement("div");
  actions.className = "comment-actions";
  const replyButton = document.createElement("button");
  replyButton.className = "comment-reply-button";
  replyButton.type = "button";
  replyButton.dataset.commentId = comment.id;
  replyButton.dataset.relatedCommentId = isReply
    ? comment.related_comment
    : comment.id;
  replyButton.dataset.commentAuthor = comment.author_username;
  replyButton.textContent = "Відповісти";
  actions.append(replyButton);
  article.append(actions);

  return article;
}

// Expects { id, author_username, created_at, text } and returns a top-level comment element.
function renderComment(comment) {
  return buildCommentElement(comment, { isReply: false });
}

// Expects a reply payload (see CommentReplySerializer) and returns a reply element.
function renderReply(reply) {
  return buildCommentElement(reply, { isReply: true });
}

window.renderComment = renderComment;
window.renderReply = renderReply;

function appendCommentToList(comment) {
  const list = document.querySelector(".comment-list");
  if (!list) {
    return;
  }
  list.querySelector(".empty-state")?.remove();
  list.prepend(renderComment(comment));
}

function appendReplyToThread(reply) {
  const root = document.querySelector(
    `.comment-list > .comment[data-comment-id="${reply.related_comment}"]`,
  );
  if (!root) {
    return;
  }

  const target = document.querySelector(
    `.comment[data-comment-id="${reply.target_comment}"] .comment-author`,
  );
  const replyData = { ...reply, target_comment_username: target?.textContent };

  let replies = document.getElementById(`comment-replies-${reply.related_comment}`);
  const viewButton = root.querySelector(".comment-view-replies-button");

  // Replies that were not loaded yet will come from the server on first expand.
  if (replies && viewButton && replies.dataset.loaded !== "true") {
    const count = Number(viewButton.dataset.replyCount) + 1;
    viewButton.dataset.replyCount = String(count);
    viewButton.textContent = `Переглянути відповіді (${count})`;
    return;
  }

  if (!replies) {
    replies = document.createElement("div");
    replies.id = `comment-replies-${reply.related_comment}`;
    replies.className = "comment-replies";
    replies.dataset.loaded = "true";
    root.querySelector(":scope > .comment-actions").after(replies);
  }
  replies.append(renderReply(replyData));
  replies.hidden = false;
  if (viewButton) {
    viewButton.setAttribute("aria-expanded", "true");
    viewButton.textContent = "Сховати відповіді";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const mainForm = document.getElementById("comment-create-form");
  const replyForm = document.getElementById("comment-reply-form");
  const replySection = document.querySelector(".comment-reply-form");
  const replyStorage = document.getElementById("comment-reply-storage");
  if (!mainForm || !replyForm || !replySection || !replyStorage) {
    return;
  }

  function attachSubmitHandler(form, getReplyCommentIds) {
    const status = form.querySelector('[role="status"]');

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      status.textContent = "";

      const formData = new FormData(form);
      try {
        const captchaCode = formData.get("captcha_1");
        const captchaHashkey = formData.get("captcha_0");
        if (!captchaCode || !captchaHashkey) {
          throw new Error("Введіть код CAPTCHA.");
        }

        const comment = await createComment({
          authorUrl: window.authorGetCreateUrl,
          commentUrl: window.commentCreateUrl,
          username: formData.get("username"),
          email: formData.get("email"),
          homePage: formData.get("home_page"),
          text: formData.get("text"),
          captchaCode,
          captchaHashkey,
          ...getReplyCommentIds(),
        });
        // The API does not return these fields yet, so use the submitted values.
        const createdComment = {
          ...comment,
          author_username: comment.author_username ?? formData.get("username"),
          created_at: comment.created_at ?? new Date().toISOString(),
        };

        if (createdComment.related_comment) {
          if (form === replyForm) {
            replyStorage.append(replySection);
            targetCommentId = null;
            relatedCommentId = null;
          }
          appendReplyToThread(createdComment);
        } else {
          appendCommentToList(createdComment);
        }

        form.reset();
        form.querySelector(".js-captcha-refresh")?.click();
      } catch (error) {
        status.textContent = error.message;
      }
    });
  }

  let targetCommentId = null;
  let relatedCommentId = null;
  attachSubmitHandler(mainForm, () => ({
    targetCommentId: null,
    relatedCommentId: null,
  }));
  attachSubmitHandler(replyForm, () => ({
    targetCommentId,
    relatedCommentId,
  }));

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const button = event.target.closest(".comment-reply-button");
    if (!button) {
      return;
    }

    const comment = button.closest(".comment");
    if (replySection.parentElement === comment) {
      replyStorage.append(replySection);
      targetCommentId = null;
      relatedCommentId = null;
      return;
    }

    targetCommentId = button.dataset.commentId;
    relatedCommentId = button.dataset.relatedCommentId;
    comment.append(replySection);
    replyForm.scrollIntoView({ behavior: "smooth", block: "center" });
    replyForm.querySelector('[name="text"]').focus();
  });

  document.querySelectorAll(".comment-view-replies-button").forEach((button) => {
    const replies = document.getElementById(
      `comment-replies-${button.dataset.commentId}`,
    );
    button.addEventListener("click", async () => {
      if (replies.dataset.loaded === "true") {
        replies.hidden = !replies.hidden;
        button.setAttribute("aria-expanded", String(!replies.hidden));
        button.textContent = replies.hidden
          ? `Переглянути відповіді (${button.dataset.replyCount})`
          : "Сховати відповіді";
        return;
      }

      button.disabled = true;
      button.textContent = "Завантаження відповідей...";
      try {
        const replyData = await getCommentReplies(
          window.commentRepliesUrl,
          button.dataset.commentId,
        );
        replyData.forEach((reply) => {
          replies.append(renderReply(reply));
        });
        replies.dataset.loaded = "true";
        replies.hidden = false;
        button.setAttribute("aria-expanded", "true");
        button.textContent = "Сховати відповіді";
      } catch (error) {
        button.textContent = `Помилка: ${error.message}`;
      } finally {
        button.disabled = false;
      }
    });
  });
});
