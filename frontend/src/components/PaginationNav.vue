<script setup>
import { config } from "../lib/config";

const { number, num_pages: numPages, has_previous: hasPrevious, has_next: hasNext } =
  config.pagination;

function href(page) {
  const params = new URLSearchParams({
    page,
    field: config.sort.field,
    orderingType: config.sort.orderingType,
  });
  return `?${params}`;
}
</script>

<template>
  <nav v-if="numPages > 1" class="pagination" aria-label="Страницы комментариев">
    <a v-if="hasPrevious" :href="href(number - 1)">Назад</a>
    <span class="page-count">Страница {{ number }} из {{ numPages }}</span>
    <a v-if="hasNext" :href="href(number + 1)">Вперёд</a>
  </nav>
</template>
