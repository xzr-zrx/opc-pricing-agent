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
const highSalesBand = computed(() => {
  const min = keyMetrics.value.high_sales_price_min
  const max = keyMetrics.value.high_sales_price_max
  return min != null && max != null ? `${formatPrice(min)} - ${formatPrice(max)}` : '—'
})
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
  const max = Math.max(1, ...counts)
  return definitions.map((bin, index) => ({ label: bin.label, count: counts[index], height: Math.max(8, Math.round((counts[index] / max) * 68)) }))
})

function strategyLabel() {
  return props.recommendation?.strategy || props.recommendation?.promotion?.strategy || '等待分析'
}
function formatPrice(value: number | null | undefined) {
  return value == null || Number.isNaN(Number(value)) ? '—' : `¥${Number(value).toFixed(2)}`
}
</script>

<template>
  <div class="overview-page">
    <section class="overview-hero">
      <div>
        <span class="hero-kicker">GOOD MORNING</span>
        <h1>掌握市场动态，制定更智能的价格策略</h1>
        <p>基于实时竞品数据与市场趋势，提供清晰的定价依据，帮助提升销量与利润。</p>
      </div>
      <div class="hero-date">
        <span>分析窗口</span>
        <strong>{{ trend?.start_date || '—' }} <i>—</i> {{ trend?.end_date || '—' }}</strong>
      </div>
    </section>

    <section class="metric-grid">
      <MetricCard label="当前售价" :value="formatPrice(product.current_price)" note="当前挂牌价" :icon="Money" tone="blue" />
      <MetricCard label="成本" :value="formatPrice(product.cost)" note="商品成本" :icon="Monitor" tone="indigo" />
      <MetricCard label="最低安全价" :value="formatPrice(minSafePrice)" note="满足最低毛利要求" :icon="TrendCharts" tone="blue" />
      <MetricCard label="毛利率" :value="`${grossMarginRate}%`" note="当前毛利空间" :icon="TrendCharts" tone="green" />
      <MetricCard label="7天市场均价" :value="formatPrice(trend?.summary.period_market_avg_price)" note="市场平均水平" :icon="TrendCharts" tone="violet" />
      <MetricCard label="库存" :value="product.stock" note="当前可用库存" :icon="Box" tone="green" />
    </section>

    <section class="primary-grid">
      <article class="surface-card trend-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">PRICE TREND</span>
            <h2>近7天价格趋势</h2>
          </div>
          <button type="button" class="text-link" @click="emit('navigate', 'trends')">查看完整趋势</button>
        </div>
        <PriceTrendChart :trend="trend" :height="190" compact />
        <div v-if="trend?.notice" class="inline-note" :class="{ warning: trend.history_insufficient }">{{ trend.notice }}</div>
      </article>

      <article class="surface-card recommendation-card">
        <div class="section-head recommendation-head">
          <div><span class="section-kicker">PRICING DECISION</span><h2>定价建议</h2></div>
          <button type="button" class="text-link" @click="emit('navigate', 'pricing')">完整建议</button>
        </div>
        <template v-if="recommendation">
          <div class="recommendation-top">
            <div class="recommended-price">
              <span>建议售价</span>
              <strong>{{ formatPrice(recommendation.suggested_price ?? product.current_price) }}</strong>
              <small>{{ strategyLabel() }}</small>
            </div>
            <div class="recommendation-meta">
              <div><span>置信度</span><b>{{ recommendation.confidence != null ? `${Math.round(recommendation.confidence * 100)}%` : '—' }}</b></div>
              <div><span>风险等级</span><b>{{ recommendation.risk_level || '—' }}</b></div>
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
            <strong class="price-value">{{ formatPrice(item.price) }}</strong>
            <span>{{ Number(item.sales || 0).toLocaleString() }}</span>
          </div>
        </div>
        <div v-else class="empty-inline">暂无竞品数据，请先执行一次竞品查询。</div>
      </article>

      <div class="insight-stack">
        <article class="surface-card distribution-card">
          <div class="mini-title"><h3>价格带分布</h3><span>{{ items.length }} 个竞品</span></div>
          <div class="bar-chart">
            <div v-for="bin in bins" :key="bin.label" class="bar-item">
              <div class="bar-track"><i :style="{ height: `${bin.height}px` }"></i></div>
              <strong>{{ bin.count }}</strong><span>{{ bin.label }}</span>
            </div>
          </div>
        </article>
        <article class="surface-card sales-band-card">
          <div class="mini-title"><h3>高销量价格区间</h3></div>
          <div class="range-visual"><span></span><b>{{ highSalesBand }}</b></div>
          <small>结合当前竞品销量与 Agent 分析结果</small>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overview-page { height:100%; min-height:0; display:grid; grid-template-rows:auto auto minmax(230px,1fr) minmax(190px,.78fr); gap:9px; }
.overview-hero { position:relative; min-height:68px; display:flex; align-items:center; justify-content:space-between; gap:20px; padding:0 8px 2px; overflow:hidden; }
.overview-hero::after { content:""; position:absolute; right:5%; top:-70px; width:420px; height:170px; border-radius:50%; background:radial-gradient(ellipse at center,rgba(83,146,255,.13),transparent 65%); transform:rotate(-8deg); pointer-events:none; }
.hero-kicker { color:#7182a0; font-size:10.5px; font-weight:700; letter-spacing:.08em; }
.overview-hero h1 { margin:5px 0 3px; color:#10203c; font-size:24px; line-height:1.08; letter-spacing:-.035em; }
.overview-hero p { margin:0; color:#7d899b; font-size:11.5px; }
.hero-date { position:relative; z-index:1; min-width:240px; padding:9px 12px; border:1px solid #e1e7ef; border-radius:10px; background:rgba(255,255,255,.82); text-align:right; }
.hero-date span,.hero-date strong { display:block; }
.hero-date span { color:#929dac; font-size:10px; }
.hero-date strong { margin-top:2px; color:#56657b; font-size:11px; font-weight:600; }
.hero-date i { padding:0 5px; color:#a2adbb; font-style:normal; }
.metric-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:8px; }
.surface-card { min-height:0; border:1px solid #e4eaf2; background:rgba(255,255,255,.96); border-radius:12px; padding:11px 13px; overflow:hidden; box-shadow:0 8px 24px rgba(55,76,110,.035); }
.primary-grid { min-height:0; display:grid; grid-template-columns:minmax(0,1.65fr) minmax(330px,.78fr); gap:9px; }
.trend-card,.recommendation-card { display:flex; flex-direction:column; }
.section-head { flex:0 0 auto; display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
.section-kicker { color:#6680ad; font-size:9.5px; font-weight:700; letter-spacing:.07em; }
h2 { margin:2px 0; color:#172641; font-size:15.5px; line-height:1.2; }
.text-link { border:0; background:transparent; color:#6281b9; cursor:pointer; font-size:10.5px; padding:4px 0; }
.text-link:hover { color:#2f6df6; }
.inline-note { margin-top:auto; padding:5px 7px; border-radius:6px; background:#eef8f5; color:#4f7468; font-size:10px; line-height:1.3; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.inline-note.warning { background:#fff6e8; color:#8b672a; }
.recommendation-head { margin-bottom:7px; }
.recommendation-top { display:grid; grid-template-columns:minmax(0,1.2fr) minmax(130px,.8fr); gap:7px; }
.recommended-price { padding:10px 11px; border-radius:10px; background:linear-gradient(145deg,#f2f7ff,#f4fbf8); border:1px solid #e1ebfa; }
.recommended-price span,.recommended-price strong,.recommended-price small { display:block; }
.recommended-price span { color:#6e7f97; font-size:10.5px; }
.recommended-price strong { margin:4px 0 3px; color:#1e63e7; font-size:27px; line-height:1; letter-spacing:-.035em; }
.recommended-price small { color:#1a9a68; font-size:10.5px; font-weight:650; }
.recommendation-meta { display:grid; gap:6px; }
.recommendation-meta div { padding:7px 8px; border:1px solid #e7ecf3; border-radius:9px; background:#f8faff; }
.recommendation-meta span,.recommendation-meta b { display:block; }
.recommendation-meta span { color:#8994a5; font-size:9.5px; }
.recommendation-meta b { margin-top:2px; color:#315ec0; font-size:12px; }
.reason-title { margin:8px 0 4px; color:#293b56; font-size:11px; font-weight:700; }
.overview-reasons { flex:1; min-height:0; max-height:94px; margin:0; padding:0 4px 0 24px; overflow-y:auto; color:#5c6a7d; font-size:10.5px; line-height:1.42; }
.overview-reasons li+li { margin-top:4px; }
.overview-reasons li::marker { color:#2f6df6; font-weight:700; }
.empty-block { flex:1; min-height:120px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:7px; text-align:center; color:#8a96a7; }
.empty-block strong { color:#536178; font-size:13px; }.empty-block span { font-size:10.5px; }
.lower-grid { min-height:0; display:grid; grid-template-columns:minmax(0,1.72fr) minmax(300px,.68fr); gap:9px; }
.competitor-card { display:flex; flex-direction:column; padding-top:9px; padding-bottom:9px; }
.competitor-head { flex:0 0 auto; display:grid; grid-template-columns:auto minmax(0,1fr) auto; align-items:center; gap:15px; margin-bottom:7px; }
.competitor-title { display:flex; align-items:baseline; gap:7px; white-space:nowrap; }.competitor-title h2{margin:0}.competitor-title span{color:#91a0b2;font-size:10px}
.market-stats { min-width:0; display:grid; grid-template-columns:repeat(5,minmax(62px,1fr)); gap:0; }
.market-stats div { padding:0 9px; border-left:1px solid #edf1f5; min-width:0; }
.market-stats span,.market-stats strong { display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.market-stats span { color:#96a1b0; font-size:9px; }.market-stats strong{margin-top:2px;color:#283852;font-size:11px}
.competitor-actions { display:flex; gap:5px; }
.compact-table { flex:1; min-height:0; overflow-y:auto; border-top:1px solid #edf1f5; }
.table-row { min-height:31px; display:grid; grid-template-columns:28px minmax(250px,1.9fr) minmax(120px,1fr) 86px 88px; gap:7px; align-items:center; padding:4px 6px; border-bottom:1px solid #f0f3f7; color:#617086; font-size:10.5px; }
.table-head { position:sticky; top:0; z-index:2; min-height:28px; background:#f7f9fc; color:#8190a4; font-size:9.5px; font-weight:650; }
.product-cell { min-width:0; display:flex; align-items:center; gap:7px; }
.product-cell img,.image-fallback { width:26px; height:26px; border-radius:6px; object-fit:cover; flex:0 0 auto; background:#eef3f9; }
.image-fallback { display:grid; place-items:center; color:#8aa0bf; font-size:9px; }
.product-cell b { min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; color:#43536b; font-size:10.5px; font-weight:600; }
.ellipsis { min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.price-value{color:#13a16c;font-size:10.5px}
.empty-inline { flex:1; min-height:90px; display:grid; place-items:center; color:#8d98a8; font-size:10.5px; }
.insight-stack { min-height:0; display:grid; grid-template-rows:minmax(0,1fr) auto; gap:9px; }
.distribution-card { display:flex; flex-direction:column; }.mini-title{display:flex;align-items:baseline;gap:7px}.mini-title h3{margin:0;color:#263650;font-size:13px}.mini-title span{color:#929dac;font-size:9.5px}
.bar-chart { flex:1; min-height:90px; display:grid; grid-template-columns:repeat(6,1fr); align-items:end; gap:6px; padding:10px 2px 0; }
.bar-item { min-width:0; text-align:center; }.bar-track{height:72px;display:flex;align-items:flex-end;justify-content:center;border-bottom:1px solid #e5eaf1}.bar-track i{display:block;width:70%;max-width:30px;border-radius:5px 5px 1px 1px;background:linear-gradient(180deg,#4b7df0,#8bb0ff)}.bar-item strong{display:block;margin-top:3px;color:#596a82;font-size:9.5px}.bar-item span{display:block;color:#98a3b2;font-size:8.5px;white-space:nowrap}
.sales-band-card { padding-top:9px; padding-bottom:9px; }.range-visual{position:relative;margin-top:12px;height:8px;border-radius:999px;background:#e8effd}.range-visual span{position:absolute;left:36%;width:30%;height:100%;border-radius:999px;background:linear-gradient(90deg,#6d6ff4,#8f65ef)}.range-visual b{position:absolute;left:51%;bottom:13px;transform:translateX(-50%);white-space:nowrap;padding:2px 6px;border-radius:5px;background:#eef1ff;color:#5661c8;font-size:9.5px}.sales-band-card small{display:block;margin-top:7px;color:#96a1b0;font-size:9px}
@media(max-height:800px) and (min-width:981px){.overview-page{grid-template-rows:auto auto minmax(205px,1fr) minmax(165px,.75fr);gap:7px}.overview-hero{min-height:56px}.overview-hero h1{font-size:21px}.overview-hero p{display:none}.surface-card{padding:9px 11px}.recommendation-card .overview-reasons{max-height:72px}.table-row{min-height:28px;padding-top:3px;padding-bottom:3px}}
@media(max-width:1280px){.metric-grid{grid-template-columns:repeat(3,1fr)}.overview-page{grid-template-rows:auto auto minmax(250px,1fr) minmax(190px,.8fr)}.market-stats div:nth-child(2),.market-stats div:nth-child(3){display:none}.market-stats{grid-template-columns:repeat(3,1fr)}}
@media(max-width:1080px){.primary-grid{grid-template-columns:1fr 330px}.lower-grid{grid-template-columns:1fr 280px}.table-row{grid-template-columns:28px minmax(210px,1.7fr) minmax(100px,1fr) 75px 75px}}
@media(max-width:980px){.overview-page{height:auto;grid-template-rows:auto}.overview-hero{align-items:flex-start;flex-direction:column}.hero-date{width:100%;text-align:left}.metric-grid{grid-template-columns:repeat(2,1fr)}.primary-grid,.lower-grid{grid-template-columns:1fr}.overview-reasons{max-height:160px}.competitor-card{min-height:360px}.insight-stack{grid-template-columns:1fr 1fr;grid-template-rows:auto}.compact-table{max-height:330px}}
@media(max-width:650px){.metric-grid,.insight-stack{grid-template-columns:1fr}.competitor-head{grid-template-columns:1fr}.market-stats{display:none}.table-row{grid-template-columns:26px minmax(180px,1fr) 75px}.table-row>span:nth-child(3),.table-row>span:nth-child(5){display:none}.overview-hero h1{font-size:21px}}
</style>
