<script setup lang="ts">
import { computed } from 'vue'
import { Box, Money, Monitor, TrendCharts } from '@element-plus/icons-vue'
import MetricCard from '../components/MetricCard.vue'
import PriceTrendChart from '../components/PriceTrendChart.vue'
import type { MarketplacePayload, Product, Recommendation, TrendPayload, ViewKey } from '../types'

const props = defineProps<{
  product: Product
  minSafePrice: number
  grossMarginRate: number
  marketplace: MarketplacePayload | null
  trend: TrendPayload | null
  recommendation: Recommendation | null
  busy: boolean
}>()
const emit = defineEmits<{
  navigate: [view: ViewKey]
  analyze: []
  search: []
}>()

const items = computed(() => props.marketplace?.items || [])
const prices = computed(() => items.value.map((item) => Number(item.price)).filter(Number.isFinite).sort((a, b) => a - b))
const averagePrice = computed(() => prices.value.length ? prices.value.reduce((sum, value) => sum + value, 0) / prices.value.length : null)
const medianPrice = computed(() => {
  if (!prices.value.length) return null
  const middle = Math.floor(prices.value.length / 2)
  return prices.value.length % 2 ? prices.value[middle] : (prices.value[middle - 1] + prices.value[middle]) / 2
})
const minPrice = computed(() => prices.value.length ? prices.value[0] : null)
const maxPrice = computed(() => prices.value.length ? prices.value[prices.value.length - 1] : null)
const totalSales = computed(() => items.value.reduce((sum, item) => sum + Number(item.sales || 0), 0))
const evidence = computed(() => (props.recommendation?.evidence_summary || []).slice(0, 5))
const keyMetrics = computed(() => props.recommendation?.key_metrics || {})

const ownTrendPercent = computed(() => {
  const series = (props.trend?.daily || []).map((day) => Number(day.own_price)).filter(Number.isFinite)
  if (series.length < 2 || !series[0]) return null
  return Number((((series[series.length - 1] - series[0]) / series[0]) * 100).toFixed(1))
})
const marketTrendPercent = computed(() => {
  const value = props.trend?.summary.trend_percent
  return value == null || !Number.isFinite(Number(value)) ? null : Number(Number(value).toFixed(1))
})
const stockStatus = computed(() => props.product.stock > 500 ? '充足' : props.product.stock > 100 ? '正常' : '偏低')
const stockTone = computed<'success' | 'warning'>(() => props.product.stock > 100 ? 'success' : 'warning')
const marginStatus = computed(() => props.grossMarginRate >= props.product.min_margin_rate + 10 ? '健康' : '关注')
const marginTone = computed<'success' | 'warning'>(() => marginStatus.value === '健康' ? 'success' : 'warning')

const highSalesMin = computed(() => Number(keyMetrics.value.high_sales_price_min))
const highSalesMax = computed(() => Number(keyMetrics.value.high_sales_price_max))
const highSalesBand = computed(() => Number.isFinite(highSalesMin.value) && Number.isFinite(highSalesMax.value)
  ? `${formatPrice(highSalesMin.value)} - ${formatPrice(highSalesMax.value)}` : '—')

const bins = computed(() => {
  const definitions = [
    { label: '<40', test: (v: number) => v < 40 },
    { label: '40-50', test: (v: number) => v >= 40 && v < 50 },
    { label: '50-60', test: (v: number) => v >= 50 && v < 60 },
    { label: '60-70', test: (v: number) => v >= 60 && v < 70 },
    { label: '70-80', test: (v: number) => v >= 70 && v < 80 },
    { label: '>80', test: (v: number) => v >= 80 },
  ]
  const counts = definitions.map((bin) => prices.value.filter(bin.test).length)
  const maxCount = Math.max(1, ...counts)
  const total = Math.max(1, prices.value.length)
  return definitions.map((bin, index) => ({
    label: bin.label,
    count: counts[index],
    percent: Math.round((counts[index] / total) * 100),
    height: Math.max(counts[index] ? 12 : 2, Math.round((counts[index] / maxCount) * 76)),
    dominant: counts[index] === maxCount && counts[index] > 0,
  }))
})
const distributionScale = computed(() => {
  const max = Math.max(1, ...bins.value.map((bin) => bin.count))
  const top = max <= 4 ? 4 : max <= 8 ? 8 : Math.ceil(max / 5) * 5
  return [top, Math.round(top * .75), Math.round(top * .5), Math.round(top * .25), 0]
})
const bandAxis = computed(() => {
  const values = prices.value.length ? prices.value : [40, 90]
  const extra = [highSalesMin.value, highSalesMax.value].filter(Number.isFinite)
  const min = Math.min(...values, ...extra)
  const max = Math.max(...values, ...extra)
  let start = Math.floor(min / 10) * 10
  let end = Math.ceil(max / 10) * 10
  if (start === end) end = start + 50
  if (end - start < 50) {
    const pad = (50 - (end - start)) / 2
    start = Math.max(0, Math.floor((start - pad) / 10) * 10)
    end = Math.ceil((end + pad) / 10) * 10
  }
  return { start, end }
})
const bandStyle = computed(() => {
  if (!Number.isFinite(highSalesMin.value) || !Number.isFinite(highSalesMax.value)) return { left: '35%', width: '30%' }
  const span = bandAxis.value.end - bandAxis.value.start
  const left = Math.max(0, Math.min(100, ((highSalesMin.value - bandAxis.value.start) / span) * 100))
  const right = Math.max(left, Math.min(100, ((highSalesMax.value - bandAxis.value.start) / span) * 100))
  return { left: `${left}%`, width: `${Math.max(4, right - left)}%` }
})
const bandTicks = computed(() => Array.from({ length: 6 }, (_, index) => Math.round(bandAxis.value.start + ((bandAxis.value.end - bandAxis.value.start) * index) / 5)))
const recommendationDelta = computed(() => {
  const suggested = props.recommendation?.suggested_price
  if (suggested == null || !props.product.current_price) return null
  return Number((((Number(suggested) - Number(props.product.current_price)) / Number(props.product.current_price)) * 100).toFixed(1))
})

function strategyLabel() {
  return props.recommendation?.strategy || props.recommendation?.promotion?.strategy || '等待分析'
}
function formatPrice(value: number | null | undefined) {
  return value == null || Number.isNaN(Number(value)) ? '—' : `¥${Number(value).toFixed(2)}`
}
function pricePosition(price: number) {
  const delta = Number(price) - Number(props.product.current_price)
  if (Math.abs(delta) < 0.01) return 'same'
  return delta > 0 ? 'higher' : 'lower'
}
</script>

<template>
  <div class="overview-page">
    <section class="overview-hero">
      <div class="hero-copy">
        <span class="hero-kicker">数据驱动 · 智能定价 · 提升盈利</span>
        <h1>让每一个价格决策更聪明</h1>
        <p>实时监控市场动态，智能生成定价建议，帮助您在激烈的市场竞争中获取更大利润。</p>
        <small v-if="trend">分析窗口 {{ trend.start_date }} — {{ trend.end_date }}</small>
      </div>
      <div class="hero-growth" aria-hidden="true">
        <div class="growth-icon">▥</div>
        <div><span>智能定价</span><strong>驱动业务增长</strong></div>
        <b>↗</b>
      </div>
    </section>

    <section class="metric-grid">
      <MetricCard label="当前售价" :value="formatPrice(product.current_price)" note="最近7天我方价格" :icon="Money" tone="blue" :trend="ownTrendPercent" />
      <MetricCard label="成本" :value="formatPrice(product.cost)" note="商品成本" :icon="Monitor" tone="blue" />
      <MetricCard label="最低安全价" :value="formatPrice(minSafePrice)" note="满足最低毛利要求" :icon="TrendCharts" tone="blue" />
      <MetricCard label="毛利率" :value="`${grossMarginRate}%`" note="当前毛利空间" :icon="TrendCharts" tone="cyan" :status="marginStatus" :status-tone="marginTone" />
      <MetricCard label="7天市场均价" :value="formatPrice(trend?.summary.period_market_avg_price)" note="市场平均水平" :icon="TrendCharts" tone="violet" :trend="marketTrendPercent" />
      <MetricCard label="库存" :value="product.stock" note="当前可用库存" :icon="Box" tone="green" :status="stockStatus" :status-tone="stockTone" />
    </section>

    <section class="primary-grid">
      <article class="surface-card trend-card">
        <div class="section-head">
          <div class="title-with-mark"><i></i><h2>近7天价格趋势</h2></div>
          <button type="button" class="text-link" @click="emit('navigate', 'trends')">查看完整趋势</button>
        </div>
        <PriceTrendChart :trend="trend" :height="198" compact />
        <div v-if="trend?.notice" class="inline-note" :class="{ warning: trend.history_insufficient }">{{ trend.notice }}</div>
      </article>

      <article class="surface-card recommendation-card">
        <div class="section-head recommendation-head">
          <div class="title-with-mark sparkle"><i>✦</i><h2>定价建议</h2></div>
          <button type="button" class="text-link" @click="emit('navigate', 'pricing')">完整建议</button>
        </div>
        <template v-if="recommendation">
          <div class="recommendation-top">
            <div class="recommended-price">
              <span>建议售价</span>
              <strong>{{ formatPrice(recommendation.suggested_price ?? product.current_price) }}</strong>
              <small v-if="recommendationDelta != null" :class="recommendationDelta > 0 ? 'rise' : 'fall'">
                {{ recommendationDelta > 0 ? '↑' : recommendationDelta < 0 ? '↓' : '—' }} 较当前价 {{ Math.abs(recommendationDelta).toFixed(1) }}%
              </small>
            </div>
            <div class="recommendation-meta">
              <div><span>建议策略</span><b class="strategy-pill">{{ strategyLabel() }}</b></div>
              <div><span>置信度</span><b>{{ recommendation.confidence != null ? `${Math.round(recommendation.confidence * 100)}%` : '—' }}</b></div>
              <div><span>风险等级</span><b class="risk-pill">{{ recommendation.risk_level || '—' }}</b></div>
            </div>
          </div>
          <div class="reason-title">建议理由</div>
          <ol class="overview-reasons ui-scroll">
            <li v-for="reason in evidence" :key="reason">{{ reason }}</li>
            <li v-if="!evidence.length">{{ recommendation.summary || '已生成定价建议，可进入定价建议页查看详情。' }}</li>
          </ol>
        </template>
        <div v-else class="empty-block">
          <strong>尚未生成定价建议</strong>
          <span>先获取竞品数据，再运行 Agent 分析。</span>
          <el-button type="primary" :loading="busy" @click="emit('analyze')">开始分析</el-button>
        </div>
      </article>
    </section>

    <section class="lower-grid">
      <article class="surface-card competitor-card">
        <div class="competitor-head">
          <div class="competitor-title"><h2>Top 15 竞品</h2><span>{{ marketplace?.count || 0 }} 个竞品</span></div>
          <div class="market-stats">
            <div><span>平均价</span><strong>{{ formatPrice(averagePrice) }}</strong></div>
            <div><span>最低价</span><strong>{{ formatPrice(minPrice) }}</strong></div>
            <div><span>最高价</span><strong>{{ formatPrice(maxPrice) }}</strong></div>
            <div><span>中位价</span><strong>{{ formatPrice(medianPrice) }}</strong></div>
            <div><span>销量参考</span><strong>{{ totalSales.toLocaleString() }}</strong></div>
          </div>
          <div class="competitor-actions"><el-button @click="emit('search')">查询竞品</el-button><el-button type="primary" @click="emit('navigate', 'competitors')">查看全部</el-button></div>
        </div>
        <div v-if="items.length" class="compact-table ui-scroll">
          <div class="table-row table-head"><span>#</span><span>商品</span><span>店铺</span><span>价格</span><span>销量参考</span></div>
          <div v-for="item in items" :key="item.competitor_id" class="table-row">
            <span>{{ item.rank }}</span>
            <div class="product-cell">
              <img v-if="item.image_url" :src="item.image_url" alt="" />
              <span v-else class="image-fallback">P</span>
              <b>{{ item.title }}</b>
            </div>
            <span class="ellipsis">{{ item.shop_name || '未知店铺' }}</span>
            <strong class="price-value" :class="`price-${pricePosition(item.price)}`">
              {{ formatPrice(item.price) }} <em>{{ pricePosition(item.price) === 'lower' ? '↓' : pricePosition(item.price) === 'higher' ? '↑' : '—' }}</em>
            </strong>
            <span>{{ Number(item.sales || 0).toLocaleString() }}</span>
          </div>
        </div>
        <div v-else class="empty-inline">暂无竞品数据，请先执行一次竞品查询。</div>
      </article>

      <div class="insight-stack">
        <article class="surface-card distribution-card">
          <div class="mini-title"><h3>价格带分布</h3><span>{{ items.length }} 个竞品</span></div>
          <div class="distribution-chart">
            <span class="axis-title">竞品数量</span>
            <div class="y-scale">
              <span v-for="tick in distributionScale" :key="tick">{{ tick }}</span>
            </div>
            <div class="distribution-plot">
              <div class="grid-lines"><i v-for="tick in distributionScale" :key="tick"></i></div>
              <div class="bars">
                <div v-for="bin in bins" :key="bin.label" class="bar-item">
                  <div class="bar-track"><i :class="{ dominant: bin.dominant }" :style="{ height: `${bin.height}px` }"></i></div>
                  <strong>{{ bin.label }}</strong>
                  <span>{{ bin.count }}个 · {{ bin.percent }}%</span>
                </div>
              </div>
            </div>
          </div>
        </article>
        <article class="surface-card sales-band-card">
          <div class="mini-title"><h3>高销量价格区间</h3><span>{{ highSalesBand }}</span></div>
          <div class="range-visual"><span :style="bandStyle"></span><b>{{ highSalesBand }}</b></div>
          <div class="range-ticks"><span v-for="tick in bandTicks" :key="tick">{{ tick }}</span></div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overview-page { height:100%; min-height:0; display:grid; grid-template-rows:auto auto minmax(230px,1fr) minmax(205px,.84fr); gap:9px; }
.overview-hero { position:relative; min-height:86px; display:flex; align-items:center; justify-content:space-between; gap:20px; padding:4px 12px 5px; overflow:hidden; }
.overview-hero::before { content:""; position:absolute; right:6%; top:-78px; width:520px; height:195px; border-radius:48% 52% 56% 44%; background:radial-gradient(ellipse at 45% 58%,rgba(72,139,246,.22),transparent 55%),radial-gradient(ellipse at 88% 62%,rgba(49,202,155,.13),transparent 40%); transform:rotate(-7deg); filter:blur(2px); pointer-events:none; }
.overview-hero::after { content:""; position:absolute; right:-2%; top:17px; width:420px; height:70px; border-radius:50%; border-top:1px solid rgba(83,145,255,.17); transform:rotate(-8deg); box-shadow:0 -10px 30px rgba(74,143,255,.04); pointer-events:none; }
.hero-copy { position:relative; z-index:1; }
.hero-kicker { color:#8d9bb0; font-size:10.5px; font-weight:600; letter-spacing:.08em; }
.overview-hero h1 { margin:6px 0 4px; color:#101f3a; font-size:27px; line-height:1.06; letter-spacing:-.04em; }
.overview-hero p { margin:0; color:#7f8da1; font-size:11.5px; }
.overview-hero small { display:block; margin-top:5px; color:#a1acba; font-size:9.5px; }
.hero-growth { position:relative; z-index:1; display:grid; grid-template-columns:40px auto 28px; align-items:center; gap:9px; min-width:245px; padding:10px 12px; border:1px solid rgba(225,233,244,.9); border-radius:12px; background:rgba(255,255,255,.72); box-shadow:0 12px 30px rgba(62,91,132,.04); backdrop-filter:blur(6px); }
.growth-icon { width:40px; height:40px; border-radius:10px; display:grid; place-items:center; color:#2f75f1; background:linear-gradient(145deg,#eef5ff,#f1fbff); font-size:19px; font-weight:800; }
.hero-growth span,.hero-growth strong { display:block; }.hero-growth span{color:#8a99ad;font-size:9.5px}.hero-growth strong{margin-top:2px;color:#58709a;font-size:12px}.hero-growth>b{color:#23b978;font-size:25px;font-weight:500}
.metric-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:8px; }
.surface-card { min-height:0; border:1px solid #e4ebf3; background:rgba(255,255,255,.98); border-radius:12px; padding:11px 13px; overflow:hidden; box-shadow:0 8px 24px rgba(55,76,110,.032); }
.primary-grid { min-height:0; display:grid; grid-template-columns:minmax(0,1.7fr) minmax(340px,.76fr); gap:9px; }
.trend-card,.recommendation-card { display:flex; flex-direction:column; }
.section-head { flex:0 0 auto; display:flex; justify-content:space-between; align-items:center; gap:12px; }
.title-with-mark { display:flex; align-items:center; gap:8px; }.title-with-mark>i{display:block;width:4px;height:17px;border-radius:99px;background:linear-gradient(180deg,#2f6df6,#735df2)}.title-with-mark.sparkle>i{width:auto;height:auto;background:none;color:#2f6df6;font-style:normal;font-size:15px}
h2 { margin:0; color:#172641; font-size:15.5px; line-height:1.2; }
.text-link { border:0; background:transparent; color:#6e87b0; cursor:pointer; font-size:10.5px; padding:4px 0; }.text-link:hover { color:#2f6df6; }
.inline-note { margin-top:auto; padding:5px 7px; border-radius:6px; background:#eef8f5; color:#4f7468; font-size:10px; line-height:1.3; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.inline-note.warning { background:#fff6e8; color:#8b672a; }
.recommendation-head { margin-bottom:7px; }
.recommendation-top { display:grid; grid-template-columns:minmax(0,1.22fr) minmax(145px,.78fr); gap:7px; }
.recommended-price { padding:10px 11px; border-radius:10px; background:linear-gradient(145deg,#f1f7ff,#f1fbf8); border:1px solid #e0eafa; }
.recommended-price span,.recommended-price strong,.recommended-price small { display:block; }.recommended-price span{color:#6e7f97;font-size:10.5px}.recommended-price strong{margin:4px 0 5px;color:#1c63e7;font-size:29px;line-height:1;letter-spacing:-.04em}.recommended-price small{width:max-content;padding:3px 6px;border-radius:6px;font-size:10px;font-weight:700}.recommended-price small.fall{color:#159867;background:#e6f8ef}.recommended-price small.rise{color:#df704f;background:#fff0ea}
.recommendation-meta { display:grid; grid-template-columns:1fr 1fr; gap:6px; }.recommendation-meta div:first-child{grid-column:1/-1}.recommendation-meta div{padding:7px 8px;border:1px solid #e7ecf3;border-radius:9px;background:#f8faff}.recommendation-meta span,.recommendation-meta b{display:block}.recommendation-meta span{color:#8994a5;font-size:9.5px}.recommendation-meta b{margin-top:2px;color:#315ec0;font-size:12px}.strategy-pill{width:max-content;padding:2px 6px;border-radius:6px;color:#159565!important;background:#e7f8ef}.risk-pill{color:#7654df!important}
.reason-title { margin:8px 0 4px; color:#293b56; font-size:11px; font-weight:700; }
.overview-reasons { flex:1; min-height:0; max-height:98px; margin:0; padding:0 5px 0 24px; overflow-y:auto; color:#5c6a7d; font-size:10.5px; line-height:1.42; }.overview-reasons li+li{margin-top:4px}.overview-reasons li::marker{color:#2f6df6;font-weight:700}
.empty-block { flex:1; min-height:120px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:7px; text-align:center; color:#8a96a7; }.empty-block strong{color:#536178;font-size:13px}.empty-block span{font-size:10.5px}
.lower-grid { min-height:0; display:grid; grid-template-columns:minmax(0,1.72fr) minmax(315px,.68fr); gap:9px; }
.competitor-card { display:flex; flex-direction:column; padding-top:9px; padding-bottom:9px; }
.competitor-head { flex:0 0 auto; display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:15px; margin-bottom:7px; }
.competitor-title { display:flex; align-items:baseline; gap:7px; white-space:nowrap; }.competitor-title h2{margin:0}.competitor-title span{color:#91a0b2;font-size:10px}
.market-stats { min-width:0; display:grid; grid-template-columns:repeat(5,minmax(62px,1fr)); gap:0; }.market-stats div{padding:0 9px;border-left:1px solid #edf1f5;min-width:0}.market-stats span,.market-stats strong{display:block;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.market-stats span{color:#96a1b0;font-size:9px}.market-stats strong{margin-top:2px;color:#283852;font-size:11px}
.competitor-actions { display:flex; gap:5px; }
.compact-table { flex:1; min-height:0; overflow-y:auto; border-top:1px solid #edf1f5; }
.table-row { min-height:31px; display:grid; grid-template-columns:28px minmax(250px,1.9fr) minmax(120px,1fr) 92px 88px; gap:7px; align-items:center; padding:4px 6px; border-bottom:1px solid #f0f3f7; color:#617086; font-size:10.5px; }
.table-head { position:sticky; top:0; z-index:2; min-height:28px; background:#f7f9fc; color:#8190a4; font-size:9.5px; font-weight:650; }
.product-cell { min-width:0; display:flex; align-items:center; gap:7px; }.product-cell img,.image-fallback{width:26px;height:26px;border-radius:6px;object-fit:cover;flex:0 0 auto;background:#eef3f9}.image-fallback{display:grid;place-items:center;color:#8aa0bf;font-size:9px}.product-cell b{min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:#43536b;font-size:10.5px;font-weight:600}.ellipsis{min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.price-value{font-size:10.5px}.price-value em{font-style:normal;font-weight:800;margin-left:2px}.price-lower{color:#0da768}.price-higher{color:#ef5665}.price-same{color:#26364f}
.empty-inline { flex:1; min-height:90px; display:grid; place-items:center; color:#8d98a8; font-size:10.5px; }
.insight-stack { min-height:0; display:grid; grid-template-rows:minmax(132px,1fr) 64px; gap:9px; }
.distribution-card { display:flex; flex-direction:column; padding-bottom:8px; }.mini-title{display:flex;align-items:baseline;gap:7px;flex:0 0 auto}.mini-title h3{margin:0;color:#263650;font-size:13px}.mini-title span{color:#768aa8;font-size:9.5px}
.distribution-chart { position:relative; flex:1; min-height:110px; display:grid; grid-template-columns:27px minmax(0,1fr); padding:12px 1px 0 13px; }
.axis-title { position:absolute; left:-2px; top:42px; color:#91a0b4; font-size:8.5px; writing-mode:vertical-rl; letter-spacing:.08em; }
.y-scale { height:82px; display:flex; flex-direction:column; justify-content:space-between; align-items:flex-end; padding-right:6px; color:#9aa6b6; font-size:8px; }
.distribution-plot { position:relative; height:112px; min-width:0; }
.grid-lines { position:absolute; inset:0 0 30px; display:flex; flex-direction:column; justify-content:space-between; pointer-events:none; }.grid-lines i{display:block;border-top:1px solid #edf1f6}
.bars { position:relative; z-index:1; height:100%; display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:5px; }
.bar-item { min-width:0; text-align:center; display:grid; grid-template-rows:82px 14px 13px; align-items:end; }.bar-track{height:82px;display:flex;align-items:flex-end;justify-content:center}.bar-track i{display:block;width:64%;max-width:30px;border-radius:5px 5px 1px 1px;background:linear-gradient(180deg,#86afff,#aecaff);box-shadow:0 4px 8px rgba(71,119,220,.08)}.bar-track i.dominant{background:linear-gradient(180deg,#3477f5,#6d9cff)}.bar-item strong{display:block;color:#63738a;font-size:8.5px;font-weight:650;white-space:nowrap}.bar-item span{display:block;color:#9aa5b3;font-size:7.8px;white-space:nowrap}
.sales-band-card { padding-top:8px; padding-bottom:7px; }.range-visual{position:relative;margin-top:12px;height:7px;border-radius:999px;background:#e5edfc}.range-visual span{position:absolute;height:100%;border-radius:999px;background:linear-gradient(90deg,#676ff2,#915df0);box-shadow:0 2px 8px rgba(118,94,236,.18)}.range-visual b{position:absolute;left:50%;bottom:12px;transform:translateX(-50%);white-space:nowrap;padding:2px 6px;border-radius:5px;background:#e9efff;color:#3569d8;font-size:9px}.range-ticks{display:flex;justify-content:space-between;margin-top:5px;color:#9aa6b6;font-size:7.5px}
@media(max-height:800px) and (min-width:981px){
  .overview-page{grid-template-rows:auto auto minmax(198px,1fr) minmax(192px,.85fr);gap:7px}.overview-hero{min-height:58px;padding-top:0;padding-bottom:0}.overview-hero h1{font-size:22px;margin:3px 0}.overview-hero p,.overview-hero small{display:none}.hero-growth{padding:7px 10px;grid-template-columns:32px auto 22px;min-width:205px}.growth-icon{width:32px;height:32px}.hero-growth>b{font-size:20px}.surface-card{padding:9px 11px}.recommendation-card .overview-reasons{max-height:70px}.table-row{min-height:28px;padding-top:3px;padding-bottom:3px}.insight-stack{grid-template-rows:minmax(124px,1fr) 58px}.distribution-chart{min-height:100px;padding-top:7px}.distribution-plot{height:105px}.bar-item{grid-template-rows:76px 13px 12px}.bar-track{height:76px}.y-scale{height:76px}.axis-title{top:35px}
}
@media(max-width:1280px){.metric-grid{grid-template-columns:repeat(3,1fr)}.overview-page{grid-template-rows:auto auto minmax(250px,1fr) minmax(205px,.8fr)}.market-stats div:nth-child(2),.market-stats div:nth-child(3){display:none}.market-stats{grid-template-columns:repeat(3,1fr)}}
@media(max-width:1080px){.primary-grid{grid-template-columns:1fr 330px}.lower-grid{grid-template-columns:1fr 295px}.table-row{grid-template-columns:28px minmax(210px,1.7fr) minmax(100px,1fr) 82px 75px}}
@media(max-width:980px){.overview-page{height:auto;grid-template-rows:auto}.overview-hero{align-items:flex-start;flex-direction:column}.hero-growth{width:100%}.metric-grid{grid-template-columns:repeat(2,1fr)}.primary-grid,.lower-grid{grid-template-columns:1fr}.overview-reasons{max-height:160px}.compact-table{max-height:390px}.insight-stack{grid-template-rows:180px 82px}.distribution-chart{min-height:130px}.distribution-plot{height:125px}.bar-item{grid-template-rows:90px 16px 14px}.bar-track,.y-scale{height:90px}}
</style>
