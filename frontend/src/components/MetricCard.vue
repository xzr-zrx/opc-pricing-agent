<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  label: string
  value: string | number
  note?: string
  icon: Component
}>()
</script>

<template>
  <article class="metric-card">
    <div class="metric-icon"><component :is="icon" /></div>
    <div class="metric-body">
      <span>{{ label }}</span>
      <strong>{{ value }}</strong>
      <small v-if="note">{{ note }}</small>
    </div>
  </article>
</template>

<style scoped>
.metric-card {
  min-height: 76px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 13px;
  border: 1px solid rgba(218, 228, 241, .96);
  border-radius: 15px;
  background: linear-gradient(145deg, rgba(253, 254, 255, .96), rgba(246, 250, 254, .94));
  box-shadow: 0 8px 22px rgba(42, 73, 116, .055), inset 0 1px 0 rgba(255,255,255,.8);
}
.metric-icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: #3f68c8;
  background: linear-gradient(145deg, #eaf2ff, #f5f9ff);
  border: 1px solid #dbe7fb;
  flex: 0 0 auto;
  box-shadow: 0 5px 12px rgba(67, 104, 189, .08);
}
.metric-icon :deep(svg) { width: 17px; height: 17px; }
.metric-body { min-width: 0; }
.metric-body > span, .metric-body > strong, .metric-body > small { display: block; }
.metric-body > span { color: #78869a; font-size: 11px; font-weight: 600; }
.metric-body > strong { margin: 3px 0 2px; color: #182842; font-size: 21px; line-height: 1.05; letter-spacing: -.035em; }
.metric-body > small { color: #9aa6b6; font-size: 10px; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
