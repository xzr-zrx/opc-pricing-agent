<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, CircleClose, Lightning } from '@element-plus/icons-vue'
import type { Product, Recommendation, TrendPayload } from '../types'

const props = defineProps<{
  product: Product
  recommendation: Recommendation | null
  trend: TrendPayload | null
  minSafePrice: number
  grossMarginRate: number
  busy: boolean
}>()
const emit = defineEmits<{ analyze: []; accept: [id: number]; reject: [id: number] }>()

const metrics = computed(() => props.recommendation?.key_metrics || props.recommendation?.promotion?.key_metrics || {})
const strategy = computed(() => props.recommendation?.strategy || props.recommendation?.promotion?.strategy || '等待分析')
const summary = computed(() => props.recommendation?.summary || props.recommendation?.promotion?.summary || '')
const confidence = computed(() => props.recommendation?.confidence ?? props.recommendation?.promotion?.confidence ?? null)
const riskLevel = computed(() => props.recommendation?.risk_level || props.recommendation?.promotion?.risk_level || '—')
const reasons = computed(() => (props.recommendation?.evidence_summary || []).slice(0, 5))
const risks = computed(() => (props.recommendation?.risk_notes || []).slice(0, 3))

function fmt(value: any) { return value == null ? '—' : `¥${Number(value).toFixed(2)}` }
function actionLabel(action?: string) {
  const map: Record<string,string> = { KEEP_PRICE:'保持价格',ADJUST_PRICE:'调整价格',LIMITED_PROMOTION:'限时促销',BUNDLE_PROMOTION:'组合促销',NEED_MORE_DATA:'补充数据',PAUSE_AND_OBSERVE:'暂停观察' }
  return map[action || ''] || action || '等待分析'
}
function trendText(value?: string) {
  const map: Record<string,string> = { up:'上涨', down:'下降', stable:'稳定', insufficient:'数据不足' }
  return map[value || ''] || value || '—'
}
function riskText(value?: string) {
  const map: Record<string,string> = { LOW:'低', MEDIUM:'中', HIGH:'高' }
  return map[value || ''] || value || '—'
}
</script>

<template>
  <div class="page-stack">
    <section class="hero-card">
      <div>
        <span class="kicker">商业定价分析</span>
        <h2>Agent 定价建议</h2>
        <p>{{ product.name }} · 分析窗口 {{ trend?.start_date || '—' }} ~ {{ trend?.end_date || '—' }}</p>
      </div>
      <el-button type="primary" :icon="Lightning" :loading="busy" @click="emit('analyze')">重新分析</el-button>
    </section>

    <section class="product-metrics">
      <article><span>当前售价</span><strong>¥{{ Number(product.current_price).toFixed(2) }}</strong></article>
      <article><span>成本</span><strong>¥{{ Number(product.cost).toFixed(2) }}</strong></article>
      <article><span>最低安全价</span><strong>¥{{ minSafePrice.toFixed(2) }}</strong></article>
      <article><span>当前毛利率</span><strong>{{ grossMarginRate }}%</strong></article>
      <article><span>库存</span><strong>{{ product.stock }}</strong></article>
      <article><span>7天市场均价</span><strong>{{ fmt(trend?.summary.period_market_avg_price) }}</strong></article>
    </section>

    <template v-if="recommendation">
      <section class="decision-card">
        <div class="price-column">
          <span>建议售价</span>
          <strong>¥{{ Number(recommendation.suggested_price ?? product.current_price).toFixed(2) }}</strong>
          <small>{{ actionLabel(recommendation.action) }}</small>
        </div>
        <div class="strategy-column">
          <div class="strategy-head"><span>建议策略</span><b>{{ strategy }}</b></div>
          <p>{{ summary || '已完成综合定价分析。' }}</p>
        </div>
        <div class="decision-meta">
          <div><span>置信度</span><strong>{{ confidence != null ? `${Math.round(Number(confidence) * 100)}%` : '—' }}</strong></div>
          <div><span>风险等级</span><strong :class="`risk-${String(riskLevel).toLowerCase()}`">{{ riskText(riskLevel) }}</strong></div>
        </div>
      </section>

      <section class="analysis-grid">
        <article class="surface-card reasons-card">
          <div class="section-title"><span class="kicker">核心理由</span><h3>为什么推荐这个价格</h3></div>
          <ol class="reason-list"><li v-for="reason in reasons" :key="reason">{{ reason }}</li></ol>
        </article>
        <article class="surface-card metrics-card">
          <div class="section-title"><span class="kicker">市场位置</span><h3>关键指标</h3></div>
          <div class="key-grid">
            <div><span>竞品样本</span><strong>{{ metrics.competitor_count ?? '—' }} / 15</strong></div>
            <div><span>市场中位价</span><strong>{{ fmt(metrics.market_median_price) }}</strong></div>
            <div><span>高销量价格带</span><strong>{{ metrics.high_sales_price_min != null && metrics.high_sales_price_max != null ? `${fmt(metrics.high_sales_price_min)} ~ ${fmt(metrics.high_sales_price_max)}` : '—' }}</strong></div>
            <div><span>市场均价</span><strong>{{ fmt(metrics.market_avg_price ?? trend?.summary.period_market_avg_price) }}</strong></div>
            <div><span>市场最低价</span><strong>{{ fmt(metrics.market_min_price ?? trend?.summary.period_market_min_price) }}</strong></div>
            <div><span>7天市场趋势</span><strong>{{ trendText(metrics.market_trend || trend?.summary.trend) }}<em v-if="metrics.market_trend_percent != null"> {{ metrics.market_trend_percent }}%</em></strong></div>
          </div>
        </article>
      </section>

      <section class="surface-card risk-card">
        <div class="risk-main">
          <div class="section-title"><span class="kicker">风险提示</span><h3>执行前需要注意</h3></div>
          <ul><li v-for="risk in risks" :key="risk">{{ risk }}</li></ul>
        </div>
        <div class="footer-actions">
          <span>数据完整度 <b>{{ recommendation.data_completeness }}</b><br/>建议 {{ recommendation.next_check_after_hours }} 小时后复查</span>
          <div><el-button type="success" :icon="CircleCheck" @click="emit('accept', recommendation.id)">接受</el-button><el-button :icon="CircleClose" @click="emit('reject', recommendation.id)">拒绝</el-button></div>
        </div>
      </section>
    </template>

    <section v-else class="surface-card empty-block">
      <strong>尚未生成定价建议</strong>
      <span>将综合前15个竞品、最近7天价格趋势、成本、毛利和库存生成商业定价结论。</span>
      <el-button type="primary" :icon="Lightning" :loading="busy" @click="emit('analyze')">开始分析</el-button>
    </section>
  </div>
</template>

<style scoped>
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto auto auto minmax(0,1fr) auto; gap:8px; }
.hero-card,.surface-card,.decision-card { border:1px solid #dfe6ee; background:#fff; border-radius:11px; }
.hero-card { padding:9px 13px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#6178a2; font-size:11px; font-weight:700; }
h2 { margin:2px 0; color:#1c2b3f; font-size:18px; }
.hero-card p { margin:0; color:#7f8b9a; font-size:11px; }
.product-metrics { display:grid; grid-template-columns:repeat(6,1fr); gap:7px; }
.product-metrics article { padding:8px 10px; border:1px solid #dfe6ee; border-radius:9px; background:#fff; }
.product-metrics span,.product-metrics strong { display:block; }
.product-metrics span { color:#7d8998; font-size:11px; }
.product-metrics strong { margin-top:3px; color:#263750; font-size:15px; line-height:1.05; }
.decision-card { padding:11px 14px; display:grid; grid-template-columns:175px minmax(0,1fr) 190px; gap:16px; align-items:center; border-left:4px solid #3568d4; }
.price-column span,.price-column strong,.price-column small { display:block; }
.price-column span { color:#748195; font-size:11px; }
.price-column strong { margin:3px 0; color:#2457bd; font-size:30px; line-height:1; letter-spacing:-.04em; }
.price-column small { color:#60718a; font-size:11px; }
.strategy-column { padding-left:15px; border-left:1px solid #e1e7ee; min-width:0; }
.strategy-head { display:flex; align-items:baseline; gap:9px; }
.strategy-head span { color:#7d8998; font-size:11px; }
.strategy-head b { color:#1f314b; font-size:17px; }
.strategy-column p { margin:5px 0 0; color:#56677e; font-size:12px; line-height:1.45; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.decision-meta { display:grid; grid-template-columns:1fr 1fr; gap:7px; }
.decision-meta div { padding:8px 9px; border:1px solid #e3e9f0; background:#f8fafc; border-radius:8px; }
.decision-meta span,.decision-meta strong { display:block; }
.decision-meta span { color:#7f8b9a; font-size:10.5px; }
.decision-meta strong { margin-top:2px; color:#2c5fc7; font-size:18px; }
.decision-meta .risk-low { color:#2f8f68; }.decision-meta .risk-medium { color:#c47a22; }.decision-meta .risk-high { color:#c34d57; }
.analysis-grid { min-height:0; display:grid; grid-template-columns:minmax(0,1.12fr) minmax(360px,.88fr); gap:8px; }
.surface-card { min-height:0; padding:10px 12px; overflow:hidden; }
.section-title h3 { margin:2px 0 8px; color:#213149; font-size:15px; }
.reason-list { margin:0; padding-left:20px; color:#4f5f75; font-size:12px; line-height:1.45; }
.reason-list li+li { margin-top:6px; }
.reason-list li::marker { color:#3568d4; font-weight:700; }
.key-grid { display:grid; grid-template-columns:1fr 1fr; gap:7px; }
.key-grid div { padding:8px 9px; border-radius:8px; background:#f7f9fc; border:1px solid #e5eaf0; min-width:0; }
.key-grid span,.key-grid strong { display:block; }
.key-grid span { color:#7f8b9a; font-size:10.5px; }
.key-grid strong { margin-top:2px; color:#304158; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.key-grid em { font-style:normal; color:#6f7f94; font-size:11px; }
.risk-card { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:14px; align-items:center; padding-top:9px; padding-bottom:9px; }
.risk-card ul { margin:0; padding-left:18px; color:#68565d; font-size:11px; line-height:1.4; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:3px 18px; }
.risk-card li { min-width:0; }
.footer-actions { min-width:275px; padding-left:13px; border-left:1px solid #e4e9ef; display:flex; justify-content:space-between; gap:10px; align-items:center; color:#748195; font-size:11px; line-height:1.4; }
.footer-actions b { color:#40516a; }
.empty-block { height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; color:#8290a2; text-align:center; }
.empty-block strong { color:#4f6078; font-size:15px; }
.empty-block span { font-size:12px; }
@media(max-width:1200px){.decision-card{grid-template-columns:160px 1fr 170px}.analysis-grid{grid-template-columns:1fr 360px}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.product-metrics{grid-template-columns:repeat(3,1fr)}.analysis-grid{grid-template-columns:1fr}.risk-card{grid-template-columns:1fr}.footer-actions{border-left:0;border-top:1px solid #e4e9ef;padding:8px 0 0}.surface-card{overflow:visible}}
@media(max-width:680px){.hero-card,.footer-actions{align-items:flex-start;flex-direction:column}.product-metrics{grid-template-columns:repeat(2,1fr)}.decision-card{grid-template-columns:1fr}.strategy-column{border-left:0;border-top:1px solid #e1e7ee;padding:10px 0 0}.key-grid{grid-template-columns:1fr}.risk-card ul{grid-template-columns:1fr}}
</style>
