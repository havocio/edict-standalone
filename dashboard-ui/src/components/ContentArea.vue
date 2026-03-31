<template>
  <div class="content">
    <EmptyState v-if="!task && !taskStore.chatReply" />
    <ChatReply
      v-else-if="taskStore.chatReply"
      :reply="taskStore.chatReply"
      @close="taskStore.clearChatReply"
    />
    <TaskDetail v-else :task="task" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTaskStore } from '../stores/task'
import EmptyState from './EmptyState.vue'
import ChatReply from './ChatReply.vue'
import TaskDetail from './TaskDetail.vue'

const taskStore = useTaskStore()
const task = computed(() => taskStore.activeTask)
</script>

<style scoped>
.content {
  flex: 1; overflow-y: auto;
  padding: 24px 28px;
  display: flex; flex-direction: column;
  gap: 20px;
}
</style>
