<script setup>
import { config } from "../lib/config";

const { field, orderingType } = config.sort;
</script>

<template>
  <form class="sort-form" method="get">
    <label for="field">Сортувати за</label>
    <select id="field" name="field">
      <option value="created" :selected="field === 'created'">Датою створення</option>
      <option value="username" :selected="field === 'username'">Ім'ям автора</option>
      <option value="email" :selected="field === 'email'">Електронною поштою</option>
    </select>
    <select name="orderingType" aria-label="Напрямок сортування">
      <option value="desc" :selected="orderingType === 'desc'">За спаданням</option>
      <option value="asc" :selected="orderingType === 'asc'">За зростанням</option>
    </select>
    <button type="submit">Застосувати</button>
  </form>
</template>
