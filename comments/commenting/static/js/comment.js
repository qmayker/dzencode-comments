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
        await createComment({
          authorUrl: window.authorGetCreateUrl,
          commentUrl: window.commentCreateUrl,
          username: formData.get("username"),
          email: formData.get("email"),
          homePage: formData.get("home_page"),
          text: formData.get("text"),
          ...getReplyCommentIds(),
        });
        window.location.reload();
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
    let loaded = false;

    button.addEventListener("click", async () => {
      if (loaded) {
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
          const article = document.createElement("article");
          article.className = "comment comment-reply";
          article.dataset.commentId = reply.id;

          const header = document.createElement("header");
          header.className = "comment-header";
          const author = document.createElement("strong");
          author.className = "comment-author";
          author.textContent = reply.author_username;
          const date = document.createElement("time");
          date.className = "comment-date";
          date.dateTime = reply.created_at;
          date.textContent = new Intl.DateTimeFormat("uk-UA", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hourCycle: "h23",
          })
            .format(new Date(reply.created_at))
            .replace(",", "");
          header.append(author, date);
          article.append(header);

          if (
            reply.target_comment !== reply.related_comment &&
            reply.target_comment_username
          ) {
            const target = document.createElement("p");
            target.className = "reply-target";
            target.textContent = `У відповідь на коментар ${reply.target_comment_username}`;
            article.append(target);
          }

          const body = document.createElement("div");
          body.className = "comment-body";
          body.innerHTML = reply.text;
          article.append(body);

          const actions = document.createElement("div");
          actions.className = "comment-actions";
          const replyButton = document.createElement("button");
          replyButton.className = "comment-reply-button";
          replyButton.type = "button";
          replyButton.dataset.commentId = reply.id;
          replyButton.dataset.relatedCommentId = reply.related_comment;
          replyButton.dataset.commentAuthor = reply.author_username;
          replyButton.textContent = "Відповісти";
          actions.append(replyButton);
          article.append(actions);

          replies.append(article);
        });
        loaded = true;
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
