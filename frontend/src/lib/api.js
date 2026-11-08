import { config } from "./config";

export function errorMessage(error) {
  return error instanceof Error ? error.message : "Невідома помилка.";
}

function getCookie(name) {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

function apiError(data, status) {
  const message =
    data && typeof data === "object"
      ? Object.values(data).flat().join(" ")
      : "";
  return new Error(message || `API request failed (${status}).`);
}

async function parseJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function postJson(url, data) {
  const isFormData = data instanceof FormData;
  const headers = { "X-CSRFToken": getCookie("csrftoken") };
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: isFormData ? data : JSON.stringify(data),
  });
  const responseData = await parseJson(response);
  if (!response.ok) {
    throw apiError(responseData, response.status);
  }
  return responseData;
}

export async function fetchStoredAuthor() {
  const token = localStorage.getItem("comment_token");
  if (!token) {
    return null;
  }

  const response = await fetch(config.urls.authorGet, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401 || response.status === 403) {
    localStorage.removeItem("comment_token");
    return null;
  }

  const responseData = await parseJson(response);
  if (!response.ok) {
    throw apiError(responseData, response.status);
  }
  return responseData;
}

export async function fetchReplies(commentId) {
  const url = new URL(config.urls.commentReplies, window.location.href);
  url.searchParams.set("comment_id", commentId);

  const response = await fetch(url);
  const responseData = await parseJson(response);
  if (!response.ok) {
    throw apiError(responseData, response.status);
  }
  if (!Array.isArray(responseData)) {
    throw new Error("The replies API returned an invalid response.");
  }
  return responseData;
}

export async function fetchCaptcha() {
  const response = await fetch(config.urls.captchaRefresh, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  });
  const result = await parseJson(response);
  if (!response.ok) {
    throw new Error(`CAPTCHA refresh failed (${response.status}).`);
  }
  if (
    typeof result?.image_url !== "string" ||
    typeof result?.key !== "string"
  ) {
    throw new Error("CAPTCHA refresh returned an invalid response.");
  }
  return {
    imageUrl: new URL(result.image_url, window.location.href).href,
    key: result.key,
  };
}

export async function fetchTextFile(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Не вдалося завантажити файл (${response.status}).`);
  }
  return response.text();
}

export async function createComment({
  storedAuthor,
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
  const authorChanged =
    storedAuthor &&
    (username !== storedAuthor.username ||
      email !== storedAuthor.email ||
      (homePage || null) !== (storedAuthor.home_page || null));
  const needsAuthor = !storedAuthor || authorChanged;

  const { captcha_token: captchaToken } = await postJson(
    config.urls.captchaVerify,
    {
      captcha_code: captchaCode,
      captcha_hashkey: captchaHashkey,
      methods: needsAuthor
        ? "author_get_create;comment_create"
        : "comment_create",
    },
  );

  let author = storedAuthor;
  if (needsAuthor) {
    author = await postJson(config.urls.authorGetCreate, {
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

  const comment = await postJson(config.urls.commentCreate, commentData);
  return { comment, author };
}
