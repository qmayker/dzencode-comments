<script setup>
import { computed } from "vue";
import { formatDate, parseDate } from "../lib/comments";

defineOptions({ name: "CommentCard" });

const props = defineProps({
  comment: { type: Object, required: true },
  isReply: { type: Boolean, default: false },
});
const emit = defineEmits([
  "reply",
  "toggle-replies",
  "open-text-file",
  "open-image",
]);

const date = computed(() => parseDate(props.comment.created_at));
const dateText = computed(() => (date.value ? formatDate(date.value) : ""));
const showTarget = computed(
  () =>
    props.isReply &&
    props.comment.target_comment_username &&
    String(props.comment.target_comment) !==
      String(props.comment.related_comment),
);
const relatedId = computed(() =>
  props.isReply ? props.comment.related_comment : props.comment.id,
);
const hasReplies = computed(
  () =>
    !props.isReply &&
    (props.comment.replyCount > 0 || props.comment.pendingReplies.length > 0),
);
const repliesLabel = computed(() => {
  const comment = props.comment;
  if (comment.repliesLoading) {
    return "Завантаження відповідей...";
  }
  if (comment.repliesError) {
    return `Помилка: ${comment.repliesError}`;
  }
  if (comment.repliesExpanded) {
    return "Сховати відповіді";
  }
  const count = Math.max(comment.replyCount, comment.pendingReplies.length);
  return `Переглянути відповіді (${count})`;
});

function openImage(event) {
  event.preventDefault();
  emit("open-image", props.comment.additional_file);
}
</script>

<template>
  <article :class="['comment', { 'comment-reply': isReply }]" :data-comment-id="comment.id">
    <header class="comment-header">
      <strong class="comment-author">{{ comment.author_username }}</strong>
      <time v-if="dateText" class="comment-date" :datetime="comment.created_at">
        {{ dateText }}
      </time>
    </header>

    <p v-if="showTarget" class="reply-target">
      У відповідь на коментар {{ comment.target_comment_username }}
    </p>

    <div class="comment-body" v-html="comment.text || ''"></div>

    <p
      v-if="comment.additional_file && comment.file_type === 'text'"
      class="comment-attachment"
    >
      <button
        type="button"
        class="js-open-text-file"
        @click="emit('open-text-file', comment.additional_file)"
      >
        Відкрити текстовий файл
      </button>
    </p>
    <p
      v-else-if="comment.additional_file && comment.file_type === 'image'"
      class="comment-attachment"
    >
      <a :href="comment.additional_file" @click="openImage">
        <img :src="comment.additional_file" alt="Зображення коментаря" loading="lazy" />
      </a>
    </p>

    <div
      v-if="!isReply && comment.pendingReplies.length"
      class="comment-replies comment-pending-replies"
    >
      <CommentCard
        v-for="reply in comment.pendingReplies"
        :key="reply.id"
        :comment="reply"
        is-reply
        @reply="emit('reply', $event)"
        @open-text-file="emit('open-text-file', $event)"
        @open-image="emit('open-image', $event)"
      />
    </div>

    <div class="comment-actions">
      <button
        class="comment-reply-button"
        type="button"
        :data-comment-id="comment.id"
        :data-related-comment-id="relatedId"
        :data-comment-author="comment.author_username"
        @click="emit('reply', comment)"
      >
        Відповісти
      </button>
      <button
        v-if="hasReplies"
        class="comment-view-replies-button"
        type="button"
        :data-comment-id="comment.id"
        :data-reply-count="comment.replyCount"
        :aria-expanded="String(comment.repliesExpanded)"
        :aria-controls="`comment-replies-${comment.id}`"
        aria-live="polite"
        :disabled="comment.repliesLoading"
        @click="emit('toggle-replies', comment)"
      >
        {{ repliesLabel }}
      </button>
    </div>

    <div
      v-if="!isReply && comment.replyCount > 0"
      :id="`comment-replies-${comment.id}`"
      class="comment-replies"
      :hidden="!comment.repliesExpanded"
    >
      <CommentCard
        v-for="reply in comment.replies"
        :key="reply.id"
        :comment="reply"
        is-reply
        @reply="emit('reply', $event)"
        @open-text-file="emit('open-text-file', $event)"
        @open-image="emit('open-image', $event)"
      />
    </div>

    <div :id="`comment-reply-target-${comment.id}`"></div>
  </article>
</template>
