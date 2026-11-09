<script setup>
import { config } from "../lib/config";

const { field, orderingType } = config.sort;
</script>

<template>
  <form class="sort-form" method="get">
    <label for="field">Сортировать по</label>
    <select id="field" name="field">
      <option value="created" :selected="field === 'created'">Дате создания</option>
      <option value="username" :selected="field === 'username'">Имени автора</option>
      <option value="email" :selected="field === 'email'">Электронной почте</option>
    </select>
    <select name="orderingType" aria-label="Порядок сортировки">
      <option value="desc" :selected="orderingType === 'desc'">По убыванию</option>
      <option value="asc" :selected="orderingType === 'asc'">По возрастанию</option>
    </select>
    <button type="submit">Применить</button>
  </form>
</template>
