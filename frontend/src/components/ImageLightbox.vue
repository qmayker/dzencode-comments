<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

const src = ref("");

function open(url) {
  src.value = url;
}

function close() {
  src.value = "";
}

function onKeydown(event) {
  if (event.key === "Escape" && src.value) {
    close();
  }
}

onMounted(() => document.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));

defineExpose({ open });
</script>

<template>
  <div
    v-if="src"
    class="image-lightbox"
    role="dialog"
    aria-modal="true"
    aria-label="Зображення коментаря"
    @click.self="close"
  >
    <button type="button" class="image-lightbox-close" aria-label="Закрити" @click="close">
      ×
    </button>
    <img :src="src" alt="Зображення коментаря" />
  </div>
</template>
