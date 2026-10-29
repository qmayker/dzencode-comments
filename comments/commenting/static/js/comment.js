async function postJson(url, data) {
    const isFormData = data instanceof FormData;
    const headers = {
        "X-CSRFToken": Cookies.get("csrftoken")
    };
    if (!isFormData) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
        method: "POST",
        headers,
        body: isFormData ? data : JSON.stringify(data),
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
  additionalFile,
  targetCommentId = null,
  relatedCommentId = null,
}) {
  const author = await postJson(authorUrl, {
    username,
    email,
    home_page: homePage || null,
  });

  const commentData = new FormData();
  commentData.set("author", author.id);
  commentData.set("text", text);
  commentData.set("captcha_0", captchaHashkey);
  commentData.set("captcha_1", captchaCode);
  if (targetCommentId) {
    commentData.set("target_comment", targetCommentId);
  }
  if (relatedCommentId) {
    commentData.set("related_comment", relatedCommentId);
  }
  if (additionalFile?.size) {
    commentData.set("additional_file", additionalFile);
  }

  return postJson(commentUrl, commentData);
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

  if (comment.additional_file && comment.file_type === "text") {
    const attachment = document.createElement("p");
    attachment.className = "comment-attachment";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "js-open-text-file";
    button.dataset.fileUrl = comment.additional_file;
    button.textContent = "Відкрити текстовий файл";
    attachment.append(button);
    article.append(attachment);
  } else if (comment.additional_file && comment.file_type === "image") {
    const attachment = document.createElement("p");
    attachment.className = "comment-attachment";
    const link = document.createElement("a");
    link.href = comment.additional_file;
    link.dataset.lightbox = "comments";
    const image = document.createElement("img");
    image.src = comment.additional_file;
    image.alt = "Зображення коментаря";
    image.loading = "lazy";
    link.append(image);
    attachment.append(link);
    article.append(attachment);
  }

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

function updateRepliesButtonLabel(button, expanded) {
  const count = button.dataset.replyCount;
  button.textContent = expanded
    ? `Сховати відповіді (${count})`
    : `Переглянути відповіді (${count})`;
}

function bindRepliesButton(button) {
  button.addEventListener("click", async () => {
    const replies = document.getElementById(
      `comment-replies-${button.dataset.commentId}`,
    );
    if (!replies) {
      return;
    }

    if (replies.dataset.loaded === "true") {
      replies.hidden = !replies.hidden;
      button.setAttribute("aria-expanded", String(!replies.hidden));
      updateRepliesButtonLabel(button, !replies.hidden);
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
      updateRepliesButtonLabel(button, true);
    } catch (error) {
      button.textContent = `Помилка: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
}

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

  const replyData = { ...reply, target_comment_username: reply.target_comment_username};

  let replies = document.getElementById(`comment-replies-${reply.related_comment}`);
  let viewButton = root.querySelector(".comment-view-replies-button");

  if (!viewButton) {
    viewButton = document.createElement("button");
    viewButton.className = "comment-view-replies-button";
    viewButton.type = "button";
    viewButton.dataset.commentId = reply.related_comment;
    viewButton.dataset.replyCount = "0";
    viewButton.setAttribute("aria-expanded", "false");
    viewButton.setAttribute(
      "aria-controls",
      `comment-replies-${reply.related_comment}`,
    );
    viewButton.setAttribute("aria-live", "polite");
    root.querySelector(":scope > .comment-actions").append(viewButton);
    bindRepliesButton(viewButton);
  }

  const count = Number(viewButton.dataset.replyCount) + 1;
  viewButton.dataset.replyCount = String(count);

  // Replies that were not loaded yet will come from the server on first expand.
  if (replies && replies.dataset.loaded !== "true") {
    updateRepliesButtonLabel(viewButton, false);
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
  viewButton.setAttribute("aria-expanded", "true");
  updateRepliesButtonLabel(viewButton, true);
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
          additionalFile: formData.get("additional_file"),
          ...getReplyCommentIds(),
        });

        if (comment.related_comment) {
          if (form === replyForm) {
            replyStorage.append(replySection);
            targetCommentId = null;
            relatedCommentId = null;
          }
          appendReplyToThread(comment);
        } else {
          appendCommentToList(comment);
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

  document
    .querySelectorAll(".comment-view-replies-button")
    .forEach(bindRepliesButton);
});
