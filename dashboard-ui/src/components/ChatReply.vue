<template>
  <div class="chat-reply fade-in">
    <div class="chat-header">
      <span class="chat-title">💬 回复</span>
      <button class="close-btn" @click="$emit('close')">✕</button>
    </div>
    <div class="chat-body">{{ reply }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ reply: string }>()
defineEmits(['close'])
</script>

<style scoped>
.chat-reply {
  background: var(--bg2);
  border: 1px solid rgba(200, 169, 110, 0.3);
  border-radius: var(--radius);
  padding: 20px 24px;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.chat-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--gold);
}
.close-btn {
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: var(--transition);
}
.close-btn:hover {
  background: var(--bg3);
  color: var(--text);
}
.chat-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
