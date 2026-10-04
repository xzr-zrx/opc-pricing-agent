<script setup lang="ts">
import { computed, type Component } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  note?: string
  icon: Component
  tone?: 'blue' | 'indigo' | 'green' | 'violet' | 'orange' | 'cyan'
  trend?: number | null
  status?: string
  statusTone?: 'success' | 'warning' | 'neutral' | 'violet'
}>(), { tone: 'blue', trend: null, statusTone: 'neutral' })

const trendClass = computed(() => {
  const value = Number(props.trend)
  if (!Number.isFinite(value) || Math.abs(value) < 0.05) return 'flat'
  return value > 0 ? 'up' : 'down'
})
const trendText = computed(() => {
  const value = Number(props.trend)
  if (!Number.isFinite(value)) return ''
  if (Math.abs(value) < 0.05) return '— 0.0%'
  return `${value > 0 ? '↑' : '↓'} ${Math.abs(value).toFixed(1)}%`
})
</script>

<template>
  <article class="metric-card" :class="`tone-${tone}`">
    <div class="metric-icon"><component :is="icon" /></div>
    <div class="metric-copy">
      <span class="metric-label">{{ label }}</span>
      <div class="metric-value-row">
        <strong>{{ value }}</strong>
        <span v-if="trend != null" class="trend-badge" :class="trendClass">{{ trendText }}</span>
        <span v-else-if="status" class="status-badge" :class="`status-${statusTone}`">{{ status }}</span>
      </div>
      <small v-if="note">{{ note }}</small>
    </div>
    <svg class="metric-spark" viewBox="0 0 58 24" aria-hidden="true">
      <path d="M2 20 C10 20 13 15 20 16 C27 17 29 7 36 10 C42 13 47 4 56 3" />
    </svg>
  </article>
</template>

<style scoped>
.metric-card {
  position: relative;
  min-width: 0;
  min-height: 78px;
  display: grid;
  grid-template-columns: 34px minmax(0,1fr);
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid #e4ebf4;
  border-radius: 12px;
  background: rgba(255,255,255,.98);
  box-shadow: 0 7px 22px rgba(45,74,118,.035);
  overflow: hidden;
}
.metric-card::after {
  content:"";
  position:absolute;
  right:-30px;
  bottom:-42px;
  width:105px;
  height:82px;
  border-radius:50%;
  background:var(--glow);
  opacity:.3;
}
.metric-icon {
  width:34px;
  height:34px;
  border-radius:10px;
  display:grid;
  place-items:center;
  color:var(--accent);
  background:var(--icon-bg);
  position:relative;
  z-index:1;
}
.metric-icon :deep(svg) { width:17px; height:17px; }
.metric-copy { min-width:0; position:relative; z-index:2; }
.metric-label { display:block; color:#53647b; font-size:11px; font-weight:650; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.metric-value-row { min-width:0; display:flex; align-items:center; gap:7px; margin-top:4px; }
.metric-value-row strong { min-width:0; color:#12213b; font-size:20px; line-height:1; letter-spacing:-.025em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.metric-copy small { display:block; margin-top:4px; color:#98a4b4; font-size:9.5px; line-height:1.15; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.trend-badge,.status-badge { flex:0 0 auto; padding:3px 6px; border-radius:7px; font-size:9.5px; font-weight:750; line-height:1; }
.trend-badge.up { color:#0a9d62; background:#e9f9f1; }
.trend-badge.down { color:#7b55e7; background:#f0ebff; }
.trend-badge.flat { color:#728199; background:#f0f3f7; }
.status-success { color:#09975e; background:#e7f8ef; }
.status-warning { color:#d47a28; background:#fff2e4; }
.status-neutral { color:#6f7e92; background:#f0f3f7; }
.status-violet { color:#7653de; background:#f0ebff; }
.metric-spark { position:absolute; right:8px; bottom:8px; width:44px; height:18px; opacity:.72; z-index:1; }
.metric-spark path { fill:none; stroke:var(--accent); stroke-width:1.6; stroke-linecap:round; }
.tone-blue { --accent:#2f6df6; --icon-bg:#edf4ff; --glow:#d9e7ff; }
.tone-indigo { --accent:#5568ed; --icon-bg:#f0f2ff; --glow:#e1e4ff; }
.tone-green { --accent:#13a772; --icon-bg:#eaf9f3; --glow:#d5f5e8; }
.tone-violet { --accent:#8359ea; --icon-bg:#f3efff; --glow:#e9e0ff; }
.tone-orange { --accent:#e88732; --icon-bg:#fff4e9; --glow:#ffe5cc; }
.tone-cyan { --accent:#16a9c7; --icon-bg:#e9f9fb; --glow:#d4f3f7; }
@media(max-height:800px) and (min-width:981px){
  .metric-card{min-height:66px;padding:8px 10px;grid-template-columns:30px minmax(0,1fr);gap:8px}
  .metric-icon{width:30px;height:30px}.metric-icon :deep(svg){width:15px;height:15px}
  .metric-value-row strong{font-size:18px}.metric-copy small{display:none}.metric-spark{width:36px;height:14px;bottom:5px}
}
</style>
