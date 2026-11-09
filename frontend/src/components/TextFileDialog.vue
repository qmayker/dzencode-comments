<script setup>
import { ref } from "vue";
import { errorMessage, fetchTextFile } from "../lib/api";

const dialog = ref(null);
const status = ref("");
const body = ref("");
const closing = ref(false);
let closeTimer = null;
let requestId = 0;

async function open(url) {
  const currentRequest = ++requestId;
  clearTimeout(closeTimer);
  closing.value = false;
  status.value = "Загрузка...";
  body.value = "";
  if (!dialog.value.open) {
    dialog.value.showModal();
  }

  try {
    const text = await fetchTextFile(url);
    if (currentRequest === requestId) {
      body.value = text;
      status.value = "";
    }
  } catch (error) {
    if (currentRequest === requestId) {
      status.value = errorMessage(error);
    }
  }
}

function close() {
  if (!dialog.value?.open || closing.value) {
    return;
  }
  requestId++;
  closing.value = true;
  closeTimer = setTimeout(finishClose, 180);
}

function finishClose() {
  clearTimeout(closeTimer);
  closing.value = false;
  if (dialog.value?.open) {
    dialog.value.close();
  }
}

defineExpose({ open });
</script>

<template>
  <dialog
    id="text-file-dialog"
    ref="dialog"
    :class="['text-file-dialog', { 'is-closing': closing }]"
    aria-labelledby="text-file-title"
    @click.self="close"
    @cancel.prevent="close"
  >
    <div class="text-file-dialog-content">
      <header class="text-file-dialog-header">
        <h2 id="text-file-title">Текстовый файл</h2>
        <button type="button" class="text-file-dialog-close" aria-label="Закрыть" @click="close">
          ×
        </button>
      </header>
      <p class="text-file-dialog-status" role="status" aria-live="polite">{{ status }}</p>
      <pre class="text-file-dialog-body">{{ body }}</pre>
    </div>
  </dialog>
</template>
