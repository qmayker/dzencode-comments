document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".comment-create form").forEach((form) => {
    const textarea = form.querySelector('textarea[name="text"]');
    if (!textarea) {
      return;
    }

    form.querySelectorAll(".tag-toolbar button[data-tag]").forEach((button) => {
      button.addEventListener("click", () => {
        const tag = button.dataset.tag;
        const openingTag = tag === "a" ? '<a href="">' : `<${tag}>`;
        const closingTag = `</${tag}>`;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.slice(start, end);
        const insertion = `${openingTag}${selectedText}${closingTag}`;

        textarea.setRangeText(insertion, start, end, "select");
        textarea.focus();

        if (selectedText) {
          textarea.setSelectionRange(
            start + openingTag.length,
            start + openingTag.length + selectedText.length,
          );
        } else {
          const cursorPosition = start + openingTag.length;
          textarea.setSelectionRange(cursorPosition, cursorPosition);
        }
      });
    });
  });
});