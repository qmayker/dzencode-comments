<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { errorMessage, fetchCaptcha } from "../lib/api";
import { config } from "../lib/config";

const props = defineProps({
  title: { type: String, required: true },
  titleId: { type: String, required: true },
  formId: { type: String, required: true },
  statusId: { type: String, required: true },
  idPrefix: { type: String, default: "id_" },
  formClass: { type: String, default: "" },
  externalStatus: { type: String, default: "" },
  submit: { type: Function, required: true },
});
const emit = defineEmits(["submitted"]);

const TAGS = [
  { tag: "i", label: "Курсив" },
  { tag: "strong", label: "Жирный" },
  { tag: "code", label: "Код" },
  { tag: "a", label: "Ссылка" },
];

const values = reactive({
  username: "",
  email: "",
  homePage: "",
  text: "",
  captchaCode: "",
});
const captcha = reactive({ imageUrl: "", key: "", loading: false });
const status = ref("");
const submitting = ref(false);
const formElement = ref(null);
const textArea = ref(null);
const fileInput = ref(null);

const visibleStatus = computed(() => status.value || props.externalStatus);
const fieldId = (name) => `${props.idPrefix}${name}`;

async function refreshCaptcha() {
  captcha.loading = true;
  try {
    const result = await fetchCaptcha();
    captcha.imageUrl = result.imageUrl;
    captcha.key = result.key;
    status.value = "";
  } catch (error) {
    status.value = `Не удалось обновить CAPTCHA: ${errorMessage(error)}`;
  } finally {
    captcha.loading = false;
  }
}

function insertTag(tag) {
  const textarea = textArea.value;
  const openingTag = tag === "a" ? '<a href="">' : `<${tag}>`;
  const closingTag = `</${tag}>`;
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = textarea.value.slice(start, end);

  textarea.setRangeText(
    `${openingTag}${selectedText}${closingTag}`,
    start,
    end,
    "select",
  );
  values.text = textarea.value;
  textarea.focus();
  textarea.setSelectionRange(
    start + openingTag.length,
    start + openingTag.length + selectedText.length,
  );
}

function fillAuthor(author, overwrite = false) {
  const fields = {
    username: author.username,
    email: author.email,
    homePage: author.home_page,
  };
  for (const [name, value] of Object.entries(fields)) {
    if (overwrite || !values[name]) {
      values[name] = value || "";
    }
  }
}

function resetForm() {
  Object.assign(values, {
    username: "",
    email: "",
    homePage: "",
    text: "",
    captchaCode: "",
  });
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

async function onSubmit() {
  if (submitting.value) {
    return;
  }

  status.value = "";
  submitting.value = true;
  try {
    if (!values.captchaCode || !captcha.key) {
      throw new Error("Введите код CAPTCHA.");
    }

    await props.submit({
      username: values.username,
      email: values.email,
      homePage: values.homePage,
      text: values.text,
      captchaCode: values.captchaCode,
      captchaHashkey: captcha.key,
      additionalFile: fileInput.value?.files[0] ?? null,
    });

    resetForm();
    emit("submitted");
    await refreshCaptcha();
  } catch (error) {
    status.value = errorMessage(error);
  } finally {
    submitting.value = false;
  }
}

function focusText() {
  textArea.value?.focus();
}

function scrollIntoView() {
  formElement.value?.scrollIntoView({ behavior: "smooth", block: "center" });
}

onMounted(refreshCaptcha);

defineExpose({ fillAuthor, focusText, scrollIntoView });
</script>

<template>
  <section
    :class="['comment-create', formClass]"
    :aria-labelledby="titleId"
  >
    <h2 :id="titleId">{{ title }}</h2>
    <form
      :id="formId"
      ref="formElement"
      data-api-form="comment-create"
      enctype="multipart/form-data"
      @submit.prevent="onSubmit"
    >
      <div class="form-field">
        <label :for="fieldId('captcha_1')">Captcha:</label>
        <img
          v-if="captcha.imageUrl"
          :src="captcha.imageUrl"
          class="captcha"
          alt="CAPTCHA"
        />
        <input type="hidden" name="captcha_0" :value="captcha.key" />
        <input
          :id="fieldId('captcha_1')"
          v-model="values.captchaCode"
          type="text"
          name="captcha_1"
          autocomplete="off"
          autocapitalize="off"
          autocorrect="off"
          spellcheck="false"
          required
        />
        <button
          type="button"
          class="js-captcha-refresh"
          :disabled="captcha.loading"
          @click="refreshCaptcha"
        >
          Обновить CAPTCHA
        </button>
      </div>

      <div class="form-field">
        <label :for="fieldId('additional_file')">Файл (необязательно):</label>
        <input
          :id="fieldId('additional_file')"
          ref="fileInput"
          type="file"
          name="additional_file"
          :accept="config.acceptedFileExtensions"
        />
      </div>

      <div class="form-field">
        <label :for="fieldId('username')">Имя:</label>
        <input
          :id="fieldId('username')"
          v-model="values.username"
          type="text"
          name="username"
          maxlength="100"
          autocomplete="username"
          required
        />
      </div>

      <div class="form-field">
        <label :for="fieldId('email')">Электронная почта:</label>
        <input
          :id="fieldId('email')"
          v-model="values.email"
          type="email"
          name="email"
          autocomplete="email"
          required
        />
      </div>

      <div class="form-field">
        <label :for="fieldId('home_page')">Домашняя страница:</label>
        <input
          :id="fieldId('home_page')"
          v-model="values.homePage"
          type="url"
          name="home_page"
          autocomplete="url"
        />
      </div>

      <div class="form-field form-field-comment">
        <label :for="fieldId('text')">Комментарий:</label>
        <div class="tag-toolbar" role="toolbar" aria-label="Форматирование комментария">
          <button
            v-for="item in TAGS"
            :key="item.tag"
            type="button"
            :data-tag="item.tag"
            :aria-label="item.label"
            @click="insertTag(item.tag)"
          >
            [{{ item.tag }}]
          </button>
        </div>
        <textarea
          :id="fieldId('text')"
          ref="textArea"
          v-model="values.text"
          name="text"
          rows="5"
          maxlength="2000"
          required
        ></textarea>
      </div>

      <button type="submit">Отправить комментарий</button>
      <p :id="statusId" role="status" aria-live="polite">{{ visibleStatus }}</p>
    </form>
  </section>
</template>
