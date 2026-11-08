<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref, computed } from "vue";
import CommentCard from "./components/CommentCard.vue";
import CommentForm from "./components/CommentForm.vue";
import ImageLightbox from "./components/ImageLightbox.vue";
import PaginationNav from "./components/PaginationNav.vue";
import SortForm from "./components/SortForm.vue";
import TextFileDialog from "./components/TextFileDialog.vue";
import {
  createComment,
  errorMessage,
  fetchReplies,
  fetchStoredAuthor,
} from "./lib/api";
import { normalizeComment } from "./lib/comments";
import { config } from "./lib/config";
import { connectCommentSocket } from "./lib/socket";

const comments = reactive(config.comments.map(normalizeComment));
const pendingNewComments = ref([]);
const countedReplyIds = new Set();
const activeReplyId = ref(null);
const activeReplyRootId = ref(null);
const currentAuthor = ref(null);
const authorStatus = ref("");

const mainForm = ref(null);
const replyForm = ref(null);
const textDialog = ref(null);
const lightbox = ref(null);

let authorLoad = Promise.resolve(null);
let socket = null;

const replyTarget = computed(() =>
  activeReplyId.value
    ? `#comment-reply-target-${activeReplyId.value}`
    : "#comment-reply-storage",
);

const sameId = (a, b) => String(a) === String(b);

function fillForms(author, overwrite = false) {
  mainForm.value?.fillAuthor(author, overwrite);
  replyForm.value?.fillAuthor(author, overwrite);
}

function submitMain(data) {
  return submit(data, false);
}

function submitReply(data) {
  return submit(data, true);
}

async function submit(data, isReply) {
  await authorLoad;
  const { comment, author } = await createComment({
    ...data,
    storedAuthor: currentAuthor.value,
    targetCommentId: isReply ? activeReplyId.value : null,
    relatedCommentId: isReply ? activeReplyRootId.value : null,
  });

  currentAuthor.value = author;
  pendingNewComments.value = pendingNewComments.value.filter(
    (item) => !sameId(item.id, comment.id),
  );
  if (comment.related_comment) {
    appendReplyToThread(comment);
    activeReplyId.value = null;
    activeReplyRootId.value = null;
  } else {
    comments.unshift(normalizeComment(comment));
  }
}

function onSubmitted() {
  if (currentAuthor.value) {
    fillForms(currentAuthor.value, true);
  }
}

async function openReplyForm(comment) {
  if (sameId(activeReplyId.value, comment.id)) {
    activeReplyId.value = null;
    activeReplyRootId.value = null;
    return;
  }

  activeReplyId.value = comment.id;
  activeReplyRootId.value = comment.related_comment || comment.id;
  await authorLoad;
  if (currentAuthor.value) {
    replyForm.value?.fillAuthor(currentAuthor.value, true);
  }
  await nextTick();
  replyForm.value?.scrollIntoView();
  replyForm.value?.focusText();
}

async function toggleReplies(comment) {
  if (comment.repliesLoaded) {
    comment.repliesExpanded = !comment.repliesExpanded;
    return;
  }
  if (comment.repliesLoading) {
    return;
  }

  comment.repliesLoading = true;
  comment.repliesError = "";
  try {
    const replies = (await fetchReplies(comment.id)).map(normalizeComment);
    for (const pending of comment.pendingReplies) {
      if (!replies.some((reply) => sameId(reply.id, pending.id))) {
        replies.unshift(pending);
      }
    }
    comment.replies = replies;
    comment.pendingReplies = [];
    comment.repliesLoaded = true;
    comment.repliesExpanded = true;
  } catch (error) {
    comment.repliesError = errorMessage(error);
  } finally {
    comment.repliesLoading = false;
  }
}

function appendReplyToThread(reply) {
  const root = comments.find((comment) => sameId(comment.id, reply.related_comment));
  if (!root) {
    return;
  }
  const exists = [...root.replies, ...root.pendingReplies].some((item) =>
    sameId(item.id, reply.id),
  );
  if (exists) {
    return;
  }

  const normalized = normalizeComment(reply);
  if (root.repliesLoaded) {
    root.replies.unshift(normalized);
    root.repliesExpanded = true;
  } else {
    root.pendingReplies.unshift(normalized);
  }
}

function receiveComment(comment) {
  if (!comment?.id) {
    return;
  }
  const known =
    comments.some((item) => sameId(item.id, comment.id)) ||
    pendingNewComments.value.some((item) => sameId(item.id, comment.id));
  if (!known) {
    pendingNewComments.value.unshift(normalizeComment(comment));
  }
}

function receiveReplyCreated(reply) {
  if (!reply?.reply_id || !reply.related_comment_id) {
    return;
  }
  const id = String(reply.reply_id);
  if (countedReplyIds.has(id)) {
    return;
  }
  const root = comments.find((comment) => sameId(comment.id, reply.related_comment_id));
  if (root) {
    root.replyCount += 1;
    countedReplyIds.add(id);
  }
}

function showPendingComments() {
  for (const comment of pendingNewComments.value.slice().reverse()) {
    if (comment.related_comment) {
      appendReplyToThread(comment);
    } else {
      comments.unshift(comment);
    }
  }
  pendingNewComments.value = [];
}

onMounted(() => {
  socket = connectCommentSocket({
    onCommentCreated: receiveComment,
    onReplyCreated: receiveReplyCreated,
  });
  authorLoad = fetchStoredAuthor()
    .then((author) => {
      currentAuthor.value = author;
      if (author) {
        fillForms(author);
      }
      return author;
    })
    .catch((error) => {
      authorStatus.value = errorMessage(error);
      return null;
    });
});

onBeforeUnmount(() => socket?.close());
</script>

<template>
  <main class="page">
    <header class="page-header">
      <p class="eyebrow">Обговорення</p>
      <h1>Коментарі</h1>
    </header>

    <CommentForm
      ref="mainForm"
      title="Залишити коментар"
      title-id="comment-create-title"
      form-id="comment-create-form"
      status-id="comment-form-status"
      :external-status="authorStatus"
      :submit="submitMain"
      @submitted="onSubmitted"
    />
    <div id="comment-reply-storage" hidden></div>
    <Teleport defer :to="replyTarget">
      <CommentForm
        ref="replyForm"
        title="Відповісти на коментар"
        title-id="comment-reply-title"
        form-id="comment-reply-form"
        status-id="comment-reply-status"
        id-prefix="reply_"
        form-class="comment-reply-form"
        :submit="submitReply"
        @submitted="onSubmitted"
      />
    </Teleport>

    <div v-if="pendingNewComments.length" id="new-comments-container" class="new-comments">
      <button id="new-comments-button" type="button" @click="showPendingComments">
        Переглянути нові коментарі ({{ pendingNewComments.length }})
      </button>
    </div>

    <SortForm />

    <section class="comment-list" aria-label="Список коментарів">
      <CommentCard
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        @reply="openReplyForm"
        @toggle-replies="toggleReplies"
        @open-text-file="textDialog.open($event)"
        @open-image="lightbox.open($event)"
      />
      <p v-if="!comments.length" class="empty-state">Коментарів поки немає.</p>
    </section>

    <TextFileDialog ref="textDialog" />
    <ImageLightbox ref="lightbox" />
    <PaginationNav />
  </main>
</template>
