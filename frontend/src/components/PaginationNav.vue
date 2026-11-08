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
  <nav v-if="numPages > 1" class="pagination" aria-label="Сторінки коментарів">
    <a v-if="hasPrevious" :href="href(number - 1)">Попередня</a>
    <span class="page-count">Сторінка {{ number }} з {{ numPages }}</span>
    <a v-if="hasNext" :href="href(number + 1)">Наступна</a>
  </nav>
</template>
