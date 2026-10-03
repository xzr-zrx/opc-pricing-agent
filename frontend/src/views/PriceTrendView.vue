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
  if (v === 'stable') return '平稳'
  return '数据不足'
})
</script>

<template>
  <div class="page-stack">
    <section class="hero-card">
      <div>
        <span class="kicker">PRICE ANALYTICS</span>
        <div class="title-row"><h2>价格趋势</h2><span>{{ product.name }}</span></div>
        <p>单次最多查看7天 · 默认读取真实入库历史</p>
      </div>
      <div class="filters">
        <el-radio-group :model-value="mode" @change="onModeChange">
          <el-radio-button value="real">真实历史</el-radio-button>
          <el-radio-button value="demo">Demo演示</el-radio-button>
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
      <article><span>区间市场均价</span><strong>{{ fmt(trend?.summary.period_market_avg_price) }}</strong></article>
      <article><span>区间最低价</span><strong>{{ fmt(trend?.summary.period_market_min_price) }}</strong></article>
      <article><span>区间最高价</span><strong>{{ fmt(trend?.summary.period_market_max_price) }}</strong></article>
      <article><span>趋势方向</span><strong>{{ trendLabel }}</strong><small v-if="trend?.summary.trend_percent != null">{{ trend.summary.trend_percent }}%</small></article>
    </section>

    <section class="surface-card chart-card">
      <div class="section-head">
        <div>
          <span class="kicker">7-DAY TREND</span>
          <h3>我方价格与市场价格波动</h3>
        </div>
        <div class="head-meta"><span>{{ trend?.source_label || '正在加载趋势数据' }}</span><b>{{ dateRange[0] }} ~ {{ dateRange[1] }}</b></div>
      </div>
      <div v-if="loading" class="loading-block">趋势数据加载中...</div>
      <PriceTrendChart v-else :trend="trend" :height="225" />
      <div v-if="trend?.notice" class="notice" :class="{ warning: trend.history_insufficient }">{{ trend.notice }}</div>
    </section>

    <section class="surface-card daily-card">
      <div class="daily-head"><div><span class="kicker">DAILY SNAPSHOT</span><h3>每日价格统计</h3></div><small>缺失日期保持为空，不伪造真实历史</small></div>
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
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto auto minmax(0,1fr) auto; gap:9px; }
.hero-card,.surface-card { border:1px solid rgba(218,228,241,.96); background:linear-gradient(145deg,rgba(253,254,255,.96),rgba(246,249,253,.94)); border-radius:16px; box-shadow:0 9px 24px rgba(42,72,110,.055), inset 0 1px 0 rgba(255,255,255,.86); }
.hero-card { padding:11px 15px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#5d79c5; font-size:9px; font-weight:800; letter-spacing:.13em; }
.title-row { display:flex; align-items:baseline; gap:8px; }
h2 { margin:2px 0; color:#182741; font-size:18px; }
.title-row>span { color:#61718a; font-size:10px; font-weight:600; }
.hero-card p { margin:0; color:#8794a7; font-size:9.5px; }
.filters { display:flex; gap:7px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }
.stats-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
.stats-grid article { padding:9px 11px; border-radius:13px; background:linear-gradient(145deg,rgba(253,254,255,.95),rgba(246,249,253,.92)); border:1px solid #dfe8f2; box-shadow:0 6px 17px rgba(39,65,102,.04); }
.stats-grid span,.stats-grid strong,.stats-grid small { display:block; }
.stats-grid span { color:#8793a5; font-size:9.5px; }
.stats-grid strong { margin-top:2px; color:#243650; font-size:17px; line-height:1.05; }
.stats-grid small { margin-top:2px; color:#7184ac; font-size:9px; }
.surface-card { min-height:0; padding:11px 14px; overflow:hidden; }
.chart-card { display:flex; flex-direction:column; }
.section-head { flex:0 0 auto; display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:1px; }
h3 { margin:2px 0; color:#1f2f49; font-size:15px; }
.head-meta { text-align:right; }
.head-meta span,.head-meta b { display:block; }
.head-meta span { color:#8996a8; font-size:9px; }
.head-meta b { margin-top:2px; color:#5f7087; font-size:9.5px; font-weight:600; }
.notice { margin-top:2px; padding:5px 8px; border-radius:8px; background:#eef7f4; color:#557b70; font-size:9.5px; line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.notice.warning { background:#fff6e7; color:#8d6a2d; }
.loading-block { flex:1; min-height:200px; display:grid; place-items:center; color:#8e9bad; font-size:11px; }
.daily-card { padding-top:9px; padding-bottom:9px; }
.daily-head { display:flex; align-items:flex-end; justify-content:space-between; gap:10px; margin-bottom:7px; }
.daily-head h3 { margin:1px 0 0; }
.daily-head small { color:#929eae; font-size:9px; }
.daily-strip { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:6px; }
.day-card { min-width:0; padding:7px 8px; border-radius:10px; background:rgba(242,247,251,.9); border:1px solid #e3ebf3; }
.day-card>strong { display:block; margin-bottom:4px; color:#34475f; font-size:10px; }
.day-card div { display:flex; justify-content:space-between; gap:4px; line-height:1.45; }
.day-card span { color:#8a96a7; font-size:8.5px; }
.day-card b { color:#435570; font-size:8.5px; font-weight:650; white-space:nowrap; }
@media(max-width:1000px){.hero-card{align-items:flex-start;flex-direction:column}.filters{justify-content:flex-start}.stats-grid{grid-template-columns:repeat(2,1fr)}.daily-strip{grid-template-columns:repeat(4,1fr)}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.surface-card{overflow:visible}}
@media(max-width:620px){.stats-grid{grid-template-columns:1fr}.daily-strip{grid-template-columns:repeat(2,1fr)}}
</style>
