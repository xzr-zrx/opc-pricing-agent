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
        <h2>价格趋势</h2>
        <p>{{ product.name }} · 单次最多查看7天，趋势默认使用真实入库数据</p>
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

    <section class="surface-card">
      <div class="section-head">
        <div>
          <span class="kicker">7-DAY TREND</span>
          <h3>我方价格与市场价格波动</h3>
          <p>{{ trend?.source_label || '正在加载趋势数据' }}</p>
        </div>
        <span class="source-badge">{{ dateRange[0] }} ~ {{ dateRange[1] }}</span>
      </div>
      <div v-if="loading" class="loading-block">趋势数据加载中...</div>
      <PriceTrendChart v-else :trend="trend" :height="380" />
      <div v-if="trend?.notice" class="notice" :class="{ warning: trend.history_insufficient }">{{ trend.notice }}</div>
    </section>

    <section class="surface-card daily-card">
      <div class="section-head">
        <div><span class="kicker">DAILY BREAKDOWN</span><h3>每日价格统计</h3><p>缺失日期保持为空，不随机生成真实历史。</p></div>
      </div>
      <el-table :data="trend?.daily || []">
        <el-table-column prop="date" label="日期" min-width="130" />
        <el-table-column label="我方价格" min-width="120"><template #default="scope">{{ fmt(scope.row.own_price) }}</template></el-table-column>
        <el-table-column label="市场均价" min-width="120"><template #default="scope">{{ fmt(scope.row.competitor_avg_price) }}</template></el-table-column>
        <el-table-column label="市场最低价" min-width="120"><template #default="scope">{{ fmt(scope.row.competitor_min_price) }}</template></el-table-column>
        <el-table-column label="市场最高价" min-width="120"><template #default="scope">{{ fmt(scope.row.competitor_max_price) }}</template></el-table-column>
        <el-table-column prop="competitor_count" label="有效竞品数" min-width="110" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.page-stack { display:grid; gap:18px; }.hero-card,.surface-card{border:1px solid #dfe7f1;background:rgba(255,255,255,.92);border-radius:20px;box-shadow:0 12px 34px rgba(39,65,102,.06)}.hero-card{padding:22px 24px;display:flex;align-items:center;justify-content:space-between;gap:18px}.kicker{color:#5c79c6;font-size:11px;font-weight:800;letter-spacing:.14em}h2{margin:5px 0;color:#182741;font-size:26px}.hero-card p,.section-head p{margin:0;color:#8794a7;font-size:13px}.filters{display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:flex-end}.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.stats-grid article{padding:17px 18px;border-radius:16px;background:rgba(255,255,255,.9);border:1px solid #e0e7f0;box-shadow:0 8px 24px rgba(39,65,102,.045)}.stats-grid span,.stats-grid strong,.stats-grid small{display:block}.stats-grid span{color:#8793a5;font-size:12px}.stats-grid strong{margin-top:6px;color:#243650;font-size:21px}.stats-grid small{margin-top:3px;color:#7184ac;font-size:11px}.surface-card{padding:22px}.section-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:10px}h3{margin:5px 0;color:#1f2f49;font-size:20px}.source-badge{border:1px solid #dce5f2;background:#f6f9fd;color:#63738b;border-radius:999px;padding:8px 12px;font-size:12px}.notice{margin-top:12px;padding:11px 13px;border-radius:12px;background:#eef7f4;color:#557b70;font-size:12px;line-height:1.6}.notice.warning{background:#fff6e7;color:#8d6a2d}.loading-block{height:380px;display:grid;place-items:center;color:#8e9bad;font-size:13px}.daily-card{overflow:hidden}@media(max-width:1000px){.hero-card{align-items:flex-start;flex-direction:column}.filters{justify-content:flex-start}.stats-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){.stats-grid{grid-template-columns:1fr}.surface-card{padding:16px}}
</style>
