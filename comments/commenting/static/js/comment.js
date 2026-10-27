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
    related_comment: relatedCommentId,
  });
}

window.createComment = createComment;

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("comment-create-form");
  if (!form) {
    return;
  }

  const status = document.getElementById("comment-form-status");

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
      });
      window.location.reload();
    } catch (error) {
      status.textContent = error.message;
    }
  });
});
