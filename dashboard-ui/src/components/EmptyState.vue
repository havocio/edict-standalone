<template>
  <div class="empty-state">
    <div class="empty-icon">🏯</div>
    <div class="empty-text">军机处待命</div>
    <div class="empty-sub">在左侧下旨，或选中一项旨意查看详情</div>
  </div>
</template>

<style scoped>
.empty-state {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: var(--text-dim); gap: 12px; text-align: center;
}
.empty-icon { font-size: 56px; opacity: .4; }
.empty-text { font-size: 15px; }
.empty-sub  { font-size: 13px; opacity: .7; }
</style>
