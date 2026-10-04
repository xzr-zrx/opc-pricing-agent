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
  min-height: 72px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #dfe6ee;
  border-radius: 10px;
  background: #fff;
}
.metric-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: #3568d4;
  background: #eef4ff;
  border: 1px solid #dce7fb;
  flex: 0 0 auto;
}
.metric-icon :deep(svg) { width: 16px; height: 16px; }
.metric-body { min-width: 0; }
.metric-body > span, .metric-body > strong, .metric-body > small { display: block; }
.metric-body > span { color: #748195; font-size: 11px; font-weight: 600; }
.metric-body > strong { margin: 3px 0 2px; color: #1d2d43; font-size: 20px; line-height: 1.05; letter-spacing: -.02em; }
.metric-body > small { color: #8d98a7; font-size: 10.5px; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
