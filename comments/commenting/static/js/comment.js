async function postJson(url, data) {
  const isFormData = data instanceof FormData;
  const headers = {
    "X-CSRFToken": Cookies.get("csrftoken"),
  };
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: isFormData ? data : JSON.stringify(data),
  });
  const responseData = await response.json();

  if (!response.ok) {
    const message = Object.values(responseData)
      .flat()
      .join(" ");
    throw new Error(message || `API request failed (${response.status}).`);
  }

  return responseData;
}

async function getStoredAuthor(url) {
  const token = localStorage.getItem("comment_token");
  if (!token) {
    return null;
  }

  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const responseData = await response.json();

  if (response.status === 401 || response.status === 403) {
    localStorage.removeItem("comment_token");
    return null;
  }
  if (!response.ok) {
    const message = Object.values(responseData)
      .flat()
      .join(" ");
    throw new Error(message || `API request failed (${response.status}).`);
  }

  return responseData;
}

function fillAuthorForm(form, author, overwrite = false) {
  for (const fieldName of ["username", "email", "home_page"]) {
    const field = form.elements.namedItem(fieldName);
    if (overwrite || !field.value) {
      field.value = author[fieldName] || "";
    }
  }
}

function fillAuthorForms(author, overwrite = false) {
  document
    .querySelectorAll('form[data-api-form="comment-create"]')
    .forEach((form) => fillAuthorForm(form, author, overwrite));
}

async function createComment({
  authorUrl,
  storedAuthor,
  commentUrl,
  username,
  email,
  homePage,
  text,
  captchaCode,
  captchaHashkey,
  captchaUrl = window.captchaVerifyUrl,
  additionalFile,
  targetCommentId = null,
  relatedCommentId = null,
}) {
  const authorChanged =
    storedAuthor &&
    (username !== storedAuthor.username ||
      email !== storedAuthor.email ||
      (homePage || null) !== (storedAuthor.home_page || null));
  const needsAuthor = !storedAuthor || authorChanged;

  const { captcha_token: captchaToken } = await postJson(captchaUrl, {
    captcha_code: captchaCode,
    captcha_hashkey: captchaHashkey,
    methods: needsAuthor ? "author_get_create;comment_create" : "comment_create",
  });

  let author = storedAuthor;
  if (needsAuthor) {
    author = await postJson(authorUrl, {
      username,
      email,
      home_page: homePage || null,
      captcha_token: captchaToken,
    });
    localStorage.setItem("comment_token", author.token);
  }

  const commentData = new FormData();
  commentData.set("author", author.id);
  commentData.set("text", text);
  commentData.set("captcha_token", captchaToken);
  if (targetCommentId) {
    commentData.set("target_comment", targetCommentId);
  }
  if (relatedCommentId) {
    commentData.set("related_comment", relatedCommentId);
  }
  if (additionalFile?.size) {
    commentData.set("additional_file", additionalFile);
  }

  const comment = await postJson(commentUrl, commentData);
  return { comment, author };
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
    ? `Сховати відповіді`
    : `Переглянути відповіді (${count})`;
}

const countedReplyIds = new Set();

function findRootComment(commentId) {
  return Array.from(
    document.querySelectorAll(".comment-list > .comment[data-comment-id]"),
  ).find((comment) => comment.dataset.commentId === String(commentId));
}

function ensureRepliesButton(root, commentId) {
  let button = root.querySelector(".comment-view-replies-button");
  if (button) {
    return button;
  }

  button = document.createElement("button");
  button.className = "comment-view-replies-button";
  button.type = "button";
  button.dataset.commentId = commentId;
  button.dataset.replyCount = "0";
  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-controls", `comment-replies-${commentId}`);
  button.setAttribute("aria-live", "polite");
  root.querySelector(":scope > .comment-actions").append(button);
  bindRepliesButton(button);
  return button;
}

function rootPendingReplies(commentId) {
  return document.getElementById(`comment-pending-replies-${commentId}`);
}

function ensurePendingRepliesContainer(root, commentId) {
  let replies = rootPendingReplies(commentId);
  if (replies) {
    return replies;
  }

  replies = document.createElement("div");
  replies.id = `comment-pending-replies-${commentId}`;
  replies.className = "comment-replies comment-pending-replies";
  root.querySelector(":scope > .comment-actions").before(replies);
  return replies;
}

function ensureRepliesContainer(root, commentId) {
  let replies = document.getElementById(`comment-replies-${commentId}`);
  if (replies) {
    return replies;
  }

  replies = document.createElement("div");
  replies.id = `comment-replies-${commentId}`;
  replies.className = "comment-replies";
  replies.dataset.loaded = "false";
  replies.hidden = true;
  root.querySelector(":scope > .comment-actions").after(replies);
  return replies;
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
        const replyAlreadyRendered = Array.from(
          replies.querySelectorAll(".comment[data-comment-id]"),
        ).some((element) => element.dataset.commentId === String(reply.id));
        if (!replyAlreadyRendered) {
          replies.append(renderReply(reply));
        }
      });
      rootPendingReplies(button.dataset.commentId)?.remove();
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
  const root = findRootComment(reply.related_comment);
  if (!root) {
    return;
  }

  const viewButton = ensureRepliesButton(root, reply.related_comment);
  const replies = ensureRepliesContainer(root, reply.related_comment);
  const replyId = String(reply.id);
  if (replies.dataset.loaded !== "true") {
    const pendingReplies = ensurePendingRepliesContainer(
      root,
      reply.related_comment,
    );
    const replyAlreadyPending = Array.from(
      pendingReplies.querySelectorAll(".comment[data-comment-id]"),
    ).some((element) => element.dataset.commentId === replyId);
    if (!replyAlreadyPending) {
      pendingReplies.prepend(renderReply(reply));
    }
    return;
  }

  const existingReply = Array.from(
    replies.querySelectorAll(".comment[data-comment-id]"),
  ).some((element) => element.dataset.commentId === replyId);
  if (existingReply) {
    return;
  }

  replies.prepend(
    renderReply({
      ...reply,
      target_comment_username: reply.target_comment_username,
    }),
  );
  replies.hidden = false;
  viewButton.setAttribute("aria-expanded", "true");
  updateRepliesButtonLabel(viewButton, true);
}

window.addEventListener("reply-created", (event) => {
  const reply = event.detail;
  if (!reply?.reply_id || !reply.related_comment_id) {
    return;
  }

  const root = findRootComment(reply.related_comment_id);
  if (!root) {
    return;
  }

  const replyId = String(reply.reply_id);
  if (countedReplyIds.has(replyId)) {
    return;
  }

  const button = ensureRepliesButton(root, reply.related_comment_id);
  ensureRepliesContainer(root, reply.related_comment_id);
  button.dataset.replyCount = String(Number(button.dataset.replyCount) + 1);
  countedReplyIds.add(replyId);
  updateRepliesButtonLabel(button, button.getAttribute("aria-expanded") === "true");
});

const pendingNewComments = [];

function removePendingNewComment(commentId) {
  const pendingIndex = pendingNewComments.findIndex(
    (comment) => String(comment.id) === String(commentId),
  );
  if (pendingIndex !== -1) {
    pendingNewComments.splice(pendingIndex, 1);
    updateNewCommentsButton();
  }
}

function updateNewCommentsButton() {
  const container = document.getElementById("new-comments-container");
  const button = document.getElementById("new-comments-button");
  if (!container || !button) {
    return;
  }

  const count = pendingNewComments.length;
  container.hidden = count === 0;
  button.textContent = `Переглянути нові коментарі (${count})`;
}

window.addEventListener("comment-created", (event) => {
  const comment = event.detail;
  if (!comment || !comment.id) {
    return;
  }

  const commentId = String(comment.id);
  const alreadyRendered = Array.from(
    document.querySelectorAll(".comment[data-comment-id]"),
  ).some((element) => element.dataset.commentId === commentId);
  if (alreadyRendered) {
    return;
  }

  if (
    pendingNewComments.some(
      (pendingComment) => String(pendingComment.id) === commentId,
    )
  ) {
    return;
  }

  pendingNewComments.unshift(comment);
  updateNewCommentsButton();
});

document.addEventListener("DOMContentLoaded", () => {
  const newCommentsButton = document.getElementById("new-comments-button");
  newCommentsButton?.addEventListener("click", () => {
    for (const comment of pendingNewComments.slice().reverse()) {
      if (comment.related_comment) {
        appendReplyToThread(comment);
      } else {
        appendCommentToList(comment);
      }
    }

    pendingNewComments.length = 0;
    updateNewCommentsButton();
  });

  const mainForm = document.getElementById("comment-create-form");
  const replyForm = document.getElementById("comment-reply-form");
  const replySection = document.querySelector(".comment-reply-form");
  const replyStorage = document.getElementById("comment-reply-storage");
  if (!mainForm || !replyForm || !replySection || !replyStorage) {
    return;
  }

  let currentAuthor = null;
  const authorLoad = getStoredAuthor(window.authorGetUrl)
    .then((author) => {
      currentAuthor = author;
      if (author) {
        fillAuthorForms(author);
      }
      return author;
    })
    .catch((error) => {
      mainForm.querySelector('[role="status"]').textContent = error.message;
      return null;
    });

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

        await authorLoad;
        const result = await createComment({
          authorUrl: window.authorGetCreateUrl,
          storedAuthor: currentAuthor,
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
        const { comment, author } = result;
        currentAuthor = author;
        removePendingNewComment(comment.id);

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
        fillAuthorForms(currentAuthor, true);
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

  document.addEventListener("click", async (event) => {
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
    await authorLoad;
    if (currentAuthor) {
      fillAuthorForm(replyForm, currentAuthor, true);
    }
    comment.append(replySection);
    replyForm.scrollIntoView({ behavior: "smooth", block: "center" });
    replyForm.querySelector('[name="text"]').focus();
  });

  document
    .querySelectorAll(".comment-view-replies-button")
    .forEach(bindRepliesButton);
});
