<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(defineProps<{
  label: string
  value: string | number
  note?: string
  icon: Component
  tone?: 'blue' | 'indigo' | 'green' | 'violet' | 'orange'
}>(), { tone: 'blue' })
</script>

<template>
  <article class="metric-card" :class="`tone-${tone}`">
    <div class="metric-copy">
      <span>{{ label }}</span>
      <strong>{{ value }}</strong>
      <small v-if="note">{{ note }}</small>
    </div>
    <div class="metric-icon"><component :is="icon" /></div>
  </article>
</template>

<style scoped>
.metric-card {
  position: relative;
  min-width: 0;
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 9px;
  padding: 10px 11px;
  border: 1px solid #e4eaf2;
  border-radius: 11px;
  background: rgba(255,255,255,.96);
  box-shadow: 0 8px 20px rgba(48,72,108,.028);
  overflow: hidden;
}
.metric-card::after { content:""; position:absolute; right:-25px; bottom:-35px; width:90px; height:70px; border-radius:50%; background:var(--glow); opacity:.34; }
.metric-copy { min-width: 0; position:relative; z-index:1; }
.metric-copy > span, .metric-copy > strong, .metric-copy > small { display: block; }
.metric-copy > span { color: #748198; font-size: 10.5px; font-weight: 600; }
.metric-copy > strong { margin: 4px 0 2px; color: #172843; font-size: 20px; line-height: 1.02; letter-spacing: -.025em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.metric-copy > small { color: #9aa5b4; font-size: 9.5px; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric-icon { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; color: var(--accent); background: var(--icon-bg); flex: 0 0 auto; position:relative; z-index:1; }
.metric-icon :deep(svg) { width: 15px; height: 15px; }
.tone-blue { --accent:#2f6df6; --icon-bg:#edf4ff; --glow:#d9e7ff; }
.tone-indigo { --accent:#5568ed; --icon-bg:#f0f2ff; --glow:#e1e4ff; }
.tone-green { --accent:#13a772; --icon-bg:#eaf9f3; --glow:#d5f5e8; }
.tone-violet { --accent:#8359ea; --icon-bg:#f3efff; --glow:#e9e0ff; }
.tone-orange { --accent:#e88732; --icon-bg:#fff4e9; --glow:#ffe5cc; }
@media(max-height:800px) and (min-width:981px){.metric-card{min-height:63px;padding:8px 10px}.metric-copy>strong{font-size:18px}.metric-copy>small{display:none}.metric-icon{width:29px;height:29px}}
</style>
