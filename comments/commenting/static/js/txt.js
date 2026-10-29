document.addEventListener("DOMContentLoaded", () => {
  const dialog = document.getElementById("text-file-dialog");
  if (!(dialog instanceof HTMLDialogElement)) {
    return;
  }

  const body = dialog.querySelector(".text-file-dialog-body");
  const status = dialog.querySelector(".text-file-dialog-status");
  const closeButton = dialog.querySelector(".text-file-dialog-close");
  if (!body || !status || !closeButton) {
    return;
  }

  let closeTimer;

  async function showTextFile(url) {
    body.textContent = "";
    status.textContent = "Завантаження файлу...";
    window.clearTimeout(closeTimer);
    dialog.classList.remove("is-closing");
    if (!dialog.open) {
      dialog.showModal();
    }

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Не вдалося завантажити файл (${response.status}).`);
      }

      body.textContent = await response.text();
      status.textContent = "";
    } catch (error) {
      status.textContent =
        error instanceof Error ? error.message : "Не вдалося відкрити файл.";
    }
  }

  function closeDialog() {
    if (!dialog.open || dialog.classList.contains("is-closing")) {
      return;
    }

    dialog.classList.add("is-closing");
    closeTimer = window.setTimeout(() => dialog.close(), 180);
  }

  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const button = event.target.closest(".js-open-text-file");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }

    const url = button.dataset.fileUrl;
    if (url) {
      showTextFile(url);
    }
  });

  closeButton.addEventListener("click", closeDialog);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      closeDialog();
    }
  });
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeDialog();
  });
  dialog.addEventListener("animationend", (event) => {
    if (event.target === dialog && dialog.classList.contains("is-closing")) {
      window.clearTimeout(closeTimer);
      dialog.close();
    }
  });
  dialog.addEventListener("close", () => {
    dialog.classList.remove("is-closing");
  });
});