<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Calendar } from '@element-plus/icons-vue'
import PriceTrendChart from '../components/PriceTrendChart.vue'
import type { Product, TrendPayload } from '../types'

const props = defineProps<{
  product: Product
  trend: TrendPayload | null
  dateRange: [string, string]
  mode: 'real' | 'demo'
  loading: boolean
}>()
const emit = defineEmits<{
  rangeChange: [range: [string, string]]
  modeChange: [mode: 'real' | 'demo']
}>()

const localDates = ref<[Date, Date]>([new Date(props.dateRange[0]), new Date(props.dateRange[1])])
watch(() => props.dateRange, (value) => { localDates.value = [new Date(value[0]), new Date(value[1])] })

function toYmd(value: Date) {
  const y = value.getFullYear()
  const m = String(value.getMonth() + 1).padStart(2, '0')
  const d = String(value.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
function onDateChange(value: [Date, Date] | null) {
  if (!value?.[0] || !value?.[1]) return
  emit('rangeChange', [toYmd(value[0]), toYmd(value[1])])
}
function onModeChange(value: string | number | boolean | undefined) {
  if (value === 'real' || value === 'demo') emit('modeChange', value)
}
function fmt(value: number | null | undefined) { return value == null ? '—' : `¥${Number(value).toFixed(2)}` }
const trendLabel = computed(() => {
  const v = props.trend?.summary.trend
  if (v === 'up') return '上涨'
  if (v === 'down') return '下降'
  if (v === 'stable') return '稳定'
  return '数据不足'
})
</script>

<template>
  <div class="page-stack">
    <section class="hero-card">
      <div>
        <span class="kicker">价格趋势</span>
        <div class="title-row"><h2>最近 7 天价格走势</h2><span>{{ product.name }}</span></div>
        <p>对比我方每日价格、市场均价和市场最低价，单次最多查看 7 天。</p>
      </div>
      <div class="filters">
        <el-radio-group :model-value="mode" @change="onModeChange">
          <el-radio-button value="real">真实历史</el-radio-button>
          <el-radio-button value="demo">Demo 演示</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="localDates"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :clearable="false"
          :editable="false"
          :prefix-icon="Calendar"
          @change="onDateChange"
        />
      </div>
    </section>

    <section class="stats-grid">
      <article><span>7天市场均价</span><strong>{{ fmt(trend?.summary.period_market_avg_price) }}</strong></article>
      <article><span>7天市场最低价</span><strong>{{ fmt(trend?.summary.period_market_min_price) }}</strong></article>
      <article><span>7天市场最高价</span><strong>{{ fmt(trend?.summary.period_market_max_price) }}</strong></article>
      <article><span>市场趋势</span><strong :class="`trend-${trend?.summary.trend || 'insufficient'}`">{{ trendLabel }}</strong><small v-if="trend?.summary.trend_percent != null">首末变化 {{ trend.summary.trend_percent }}%</small></article>
    </section>

    <section class="surface-card chart-card">
      <div class="section-head">
        <div>
          <span class="kicker">每日波动</span>
          <h3>我方价格 vs 市场价格</h3>
        </div>
        <div class="head-meta"><span>{{ trend?.source_label || '正在加载趋势数据' }}</span><b>{{ dateRange[0] }} ~ {{ dateRange[1] }}</b></div>
      </div>
      <div v-if="loading" class="loading-block">趋势数据加载中...</div>
      <PriceTrendChart v-else :trend="trend" :height="260" />
      <div v-if="trend?.notice" class="notice" :class="{ warning: trend.history_insufficient }">{{ trend.notice }}</div>
    </section>

    <section class="surface-card daily-card">
      <div class="daily-head"><div><span class="kicker">每日明细</span><h3>7 天价格快照</h3></div><small>缺失日期保持为空，不补造历史</small></div>
      <div class="daily-strip">
        <article v-for="day in trend?.daily || []" :key="day.date" class="day-card">
          <strong>{{ day.date.slice(5) }}</strong>
          <div><span>我方</span><b>{{ fmt(day.own_price) }}</b></div>
          <div><span>均价</span><b>{{ fmt(day.competitor_avg_price) }}</b></div>
          <div><span>最低</span><b>{{ fmt(day.competitor_min_price) }}</b></div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto auto minmax(0,1fr) auto; gap:8px; }
.hero-card,.surface-card { border:1px solid #dfe6ee; background:#fff; border-radius:11px; }
.hero-card { padding:9px 13px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#6178a2; font-size:11px; font-weight:700; }
.title-row { display:flex; align-items:baseline; gap:9px; }
h2 { margin:2px 0; color:#1c2b3f; font-size:18px; }
.title-row>span { color:#607088; font-size:12px; font-weight:600; }
.hero-card p { margin:0; color:#7f8b9a; font-size:11px; }
.filters { display:flex; gap:7px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }
.stats-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
.stats-grid article { padding:8px 11px; border-radius:9px; background:#fff; border:1px solid #dfe6ee; }
.stats-grid span,.stats-grid strong,.stats-grid small { display:block; }
.stats-grid span { color:#7d8998; font-size:11px; }
.stats-grid strong { margin-top:3px; color:#263750; font-size:17px; line-height:1.05; }
.stats-grid small { margin-top:3px; color:#8290a2; font-size:10.5px; }
.trend-up { color:#2f8f68!important; }.trend-down { color:#c47a22!important; }.trend-stable { color:#3568d4!important; }
.surface-card { min-height:0; padding:10px 12px; overflow:hidden; }
.chart-card { display:flex; flex-direction:column; }
.section-head { flex:0 0 auto; display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:2px; }
h3 { margin:2px 0; color:#223149; font-size:16px; }
.head-meta { text-align:right; }
.head-meta span,.head-meta b { display:block; }
.head-meta span { color:#7f8b9a; font-size:10.5px; }
.head-meta b { margin-top:2px; color:#5d6e84; font-size:11px; font-weight:600; }
.notice { margin-top:2px; padding:6px 8px; border-radius:7px; background:#eef8f4; color:#4e7468; font-size:10.5px; line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.notice.warning { background:#fff6e8; color:#8b672a; }
.loading-block { flex:1; min-height:220px; display:grid; place-items:center; color:#8793a2; font-size:12px; }
.daily-card { padding-top:8px; padding-bottom:8px; }
.daily-head { display:flex; align-items:flex-end; justify-content:space-between; gap:10px; margin-bottom:6px; }
.daily-head h3 { margin:1px 0 0; }
.daily-head small { color:#8793a2; font-size:10.5px; }
.daily-strip { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:6px; }
.day-card { min-width:0; padding:7px 8px; border-radius:8px; background:#f8fafc; border:1px solid #e5eaf0; }
.day-card>strong { display:block; margin-bottom:4px; color:#34475f; font-size:11.5px; }
.day-card div { display:flex; justify-content:space-between; gap:4px; line-height:1.45; }
.day-card span { color:#8491a1; font-size:10.5px; }
.day-card b { color:#435570; font-size:10.5px; font-weight:650; white-space:nowrap; }
@media(max-height:800px) and (min-width:981px){.hero-card p{display:none}.chart-card :deep(.trend-chart){height:225px!important}}
@media(max-width:1000px){.hero-card{align-items:flex-start;flex-direction:column}.filters{justify-content:flex-start}.stats-grid{grid-template-columns:repeat(2,1fr)}.daily-strip{grid-template-columns:repeat(4,1fr)}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.surface-card{overflow:visible}}
@media(max-width:620px){.stats-grid{grid-template-columns:1fr}.daily-strip{grid-template-columns:repeat(2,1fr)}}
</style>
