document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".comment-create form").forEach((form) => {
    const refreshButton = form.querySelector(".js-captcha-refresh");
    const captchaField = refreshButton?.closest(".form-field");
    const status = form.querySelector('[role="status"]');

    if (!refreshButton || !captchaField) {
      return;
    }

    refreshButton.addEventListener("click", async () => {
      refreshButton.disabled = true;
      try {
        const response = await fetch("/captcha/refresh/", {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const result = await response.json();

        if (!response.ok) {
          throw new Error(`CAPTCHA refresh failed (${response.status}).`);
        }
        if (
          typeof result.image_url !== "string" ||
          typeof result.key !== "string"
        ) {
          throw new Error("CAPTCHA refresh returned an invalid response.");
        }

        const image = captchaField.querySelector(".captcha");
        const keyInput = captchaField.querySelector('input[type="hidden"]');
        if (!image || !keyInput) {
          throw new Error("CAPTCHA controls are missing from the form.");
        }

        image.src = new URL(result.image_url, window.location.href).href;
        keyInput.value = result.key;
        if (status) {
          status.textContent = "";
        }
      } catch (error) {
        if (status) {
          status.textContent = `Не вдалося оновити CAPTCHA: ${error.message}`;
        }
      } finally {
        refreshButton.disabled = false;
      }
    });
  });
});