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
  min-height: 116px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 1px solid #dfe7f1;
  border-radius: 18px;
  background: rgba(255, 255, 255, .92);
  box-shadow: 0 10px 30px rgba(39, 65, 102, .06);
}
.metric-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #426bd7;
  background: linear-gradient(145deg, #edf4ff, #f7faff);
  border: 1px solid #dfe8fb;
  flex: 0 0 auto;
}
.metric-icon :deep(svg) { width: 21px; height: 21px; }
.metric-body > span, .metric-body > strong, .metric-body > small { display: block; }
.metric-body > span { color: #758399; font-size: 13px; font-weight: 600; }
.metric-body > strong { margin: 6px 0 4px; color: #182640; font-size: 29px; line-height: 1; letter-spacing: -.04em; }
.metric-body > small { color: #9aa6b6; font-size: 12px; line-height: 1.35; }
</style>
