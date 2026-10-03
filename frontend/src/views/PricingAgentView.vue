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
function fmt(value: any) { return value == null ? '—' : `¥${Number(value).toFixed(2)}` }
function actionLabel(action?: string) {
  const map: Record<string,string> = { KEEP_PRICE:'保持价格',ADJUST_PRICE:'调整价格',LIMITED_PROMOTION:'限时促销',BUNDLE_PROMOTION:'组合促销',NEED_MORE_DATA:'补充数据',PAUSE_AND_OBSERVE:'暂停观察' }
  return map[action || ''] || action || '等待分析'
}
</script>

<template>
  <div class="page-stack">
    <section class="hero-card">
      <div>
        <span class="kicker">AI PRICING DECISION</span>
        <h2>Agent 定价建议</h2>
        <p>{{ product.name }} · 分析窗口 {{ trend?.start_date || '—' }} ~ {{ trend?.end_date || '—' }}</p>
      </div>
      <el-button type="primary" :icon="Lightning" :loading="busy" @click="emit('analyze')">开始 Agent 定价分析</el-button>
    </section>

    <section class="product-metrics">
      <article><span>当前售价</span><strong>¥{{ product.current_price }}</strong></article>
      <article><span>成本</span><strong>¥{{ product.cost }}</strong></article>
      <article><span>安全价</span><strong>¥{{ minSafePrice }}</strong></article>
      <article><span>毛利率</span><strong>{{ grossMarginRate }}%</strong></article>
      <article><span>库存</span><strong>{{ product.stock }}</strong></article>
      <article><span>7天市场均价</span><strong>{{ fmt(trend?.summary.period_market_avg_price) }}</strong></article>
    </section>

    <template v-if="recommendation">
      <section class="decision-card">
        <div class="price-column">
          <span>建议售价</span>
          <strong>¥{{ recommendation.suggested_price ?? product.current_price }}</strong>
          <small>{{ actionLabel(recommendation.action) }}</small>
        </div>
        <div class="strategy-column">
          <span>建议策略</span>
          <strong>{{ strategy }}</strong>
          <p>{{ summary || '已完成定价分析。' }}</p>
        </div>
        <div class="confidence-ring">
          <span>置信度</span>
          <strong>{{ confidence != null ? `${Math.round(Number(confidence) * 100)}%` : '—' }}</strong>
          <small>风险 {{ riskLevel }}</small>
        </div>
      </section>

      <section class="analysis-grid">
        <article class="surface-card reasons-card">
          <div class="section-title"><span class="kicker">WHY</span><h3>建议理由</h3></div>
          <ol class="reason-list"><li v-for="reason in recommendation.evidence_summary" :key="reason">{{ reason }}</li></ol>
        </article>
        <article class="surface-card">
          <div class="section-title"><span class="kicker">KEY METRICS</span><h3>关键数据</h3></div>
          <div class="key-grid">
            <div><span>当前价格</span><strong>{{ fmt(metrics.current_price ?? product.current_price) }}</strong></div>
            <div><span>市场均价</span><strong>{{ fmt(metrics.market_avg_price ?? trend?.summary.period_market_avg_price) }}</strong></div>
            <div><span>市场最低价</span><strong>{{ fmt(metrics.market_min_price ?? trend?.summary.period_market_min_price) }}</strong></div>
            <div><span>安全底价</span><strong>{{ fmt(metrics.min_safe_price ?? minSafePrice) }}</strong></div>
            <div><span>市场趋势</span><strong>{{ metrics.market_trend || trend?.summary.trend || '—' }}</strong></div>
            <div><span>有效历史</span><strong>{{ metrics.market_data_days ?? trend?.summary.market_data_days ?? 0 }} 天</strong></div>
          </div>
        </article>
      </section>

      <section class="surface-card risk-card">
        <div class="risk-main">
          <div class="section-title"><span class="kicker">RISK CONTROL</span><h3>风险提示</h3></div>
          <ul><li v-for="risk in recommendation.risk_notes" :key="risk">{{ risk }}</li></ul>
        </div>
        <div class="footer-actions">
          <span>数据完整度 <b>{{ recommendation.data_completeness }}</b><br/>建议 {{ recommendation.next_check_after_hours }} 小时后复查</span>
          <div><el-button type="success" :icon="CircleCheck" @click="emit('accept', recommendation.id)">接受</el-button><el-button type="danger" :icon="CircleClose" @click="emit('reject', recommendation.id)">拒绝</el-button></div>
        </div>
      </section>
    </template>

    <section v-else class="surface-card empty-block">
      <strong>尚未运行 Agent 定价分析</strong>
      <span>Agent 会综合最近7天市场价格、当前Top5、成本、库存和销量后生成建议。</span>
      <el-button type="primary" :icon="Lightning" :loading="busy" @click="emit('analyze')">开始 Agent 分析</el-button>
    </section>
  </div>
</template>

<style scoped>
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto auto auto minmax(0,1fr) auto; gap:9px; }
.hero-card,.surface-card,.decision-card { border:1px solid rgba(218,228,241,.96); background:linear-gradient(145deg,rgba(253,254,255,.96),rgba(246,249,253,.94)); border-radius:16px; box-shadow:0 9px 24px rgba(42,72,110,.055), inset 0 1px 0 rgba(255,255,255,.86); }
.hero-card { padding:11px 15px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#5d79c5; font-size:9px; font-weight:800; letter-spacing:.13em; }
h2 { margin:2px 0; color:#182741; font-size:18px; }
.hero-card p { margin:0; color:#8794a7; font-size:9.5px; }
.product-metrics { display:grid; grid-template-columns:repeat(6,1fr); gap:7px; }
.product-metrics article { padding:8px 10px; border:1px solid #e0e8f1; border-radius:12px; background:linear-gradient(145deg,rgba(253,254,255,.95),rgba(246,249,253,.92)); }
.product-metrics span,.product-metrics strong { display:block; }
.product-metrics span { color:#8793a5; font-size:9px; }
.product-metrics strong { margin-top:2px; color:#263751; font-size:15px; line-height:1.05; }
.decision-card { padding:12px 15px; display:grid; grid-template-columns:165px 1fr 125px; gap:15px; align-items:center; background:linear-gradient(125deg,rgba(247,250,255,.98),rgba(237,245,255,.97)); }
.price-column span,.price-column strong,.price-column small { display:block; }
.price-column span { color:#7c899d; font-size:9.5px; }
.price-column strong { margin:2px 0; color:#244b9b; font-size:30px; line-height:1; letter-spacing:-.05em; }
.price-column small { color:#60728e; font-size:9.5px; }
.strategy-column { padding-left:15px; border-left:1px solid #dce6f3; min-width:0; }
.strategy-column span { color:#7d8a9d; font-size:9.5px; }
.strategy-column strong { display:block; margin-top:2px; color:#1f304c; font-size:17px; }
.strategy-column p { margin:4px 0 0; color:#5e6d82; font-size:10.5px; line-height:1.45; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.confidence-ring { text-align:center; padding:10px 8px; border-radius:13px; background:rgba(255,255,255,.88); border:1px solid #e1e8f1; }
.confidence-ring span,.confidence-ring strong,.confidence-ring small { display:block; }
.confidence-ring span { color:#8793a5; font-size:9px; }
.confidence-ring strong { margin:2px 0; color:#2d5fc4; font-size:21px; }
.confidence-ring small { color:#7d8a9b; font-size:9px; }
.analysis-grid { min-height:0; display:grid; grid-template-columns:1.15fr .85fr; gap:9px; }
.surface-card { min-height:0; padding:11px 13px; overflow:hidden; }
.section-title h3 { margin:2px 0 8px; color:#21314a; font-size:14px; }
.reason-list { margin:0; padding-left:18px; color:#58677d; font-size:10.5px; line-height:1.5; }
.reason-list li+li { margin-top:5px; }
.key-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.key-grid div { padding:7px 8px; border-radius:9px; background:rgba(241,246,251,.9); border:1px solid #e7edf4; }
.key-grid span,.key-grid strong { display:block; }
.key-grid span { color:#8c98a9; font-size:8.5px; }
.key-grid strong { margin-top:2px; color:#304058; font-size:10.5px; }
.risk-card { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:14px; align-items:center; padding-top:9px; padding-bottom:9px; }
.risk-card ul { margin:0; padding-left:17px; color:#6c5960; font-size:9.5px; line-height:1.4; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:2px 18px; }
.risk-card li { min-width:0; }
.footer-actions { min-width:235px; padding-left:13px; border-left:1px solid #e4eaf2; display:flex; justify-content:space-between; gap:9px; align-items:center; color:#7d8a9c; font-size:9px; line-height:1.35; }
.footer-actions b { color:#40516b; }
.empty-block { height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:7px; color:#8f9bad; text-align:center; }
.empty-block strong { color:#52627a; font-size:14px; }
.empty-block span { font-size:10px; }
@media(max-width:1200px){.decision-card{grid-template-columns:150px 1fr 110px}.product-metrics{grid-template-columns:repeat(6,1fr)}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.product-metrics{grid-template-columns:repeat(3,1fr)}.analysis-grid{grid-template-columns:1fr}.risk-card{grid-template-columns:1fr}.footer-actions{border-left:0;border-top:1px solid #e4eaf2;padding:8px 0 0}.surface-card{overflow:visible}}
@media(max-width:680px){.hero-card,.footer-actions{align-items:flex-start;flex-direction:column}.product-metrics{grid-template-columns:repeat(2,1fr)}.decision-card{grid-template-columns:1fr}.strategy-column{border-left:0;border-top:1px solid #dce6f3;padding:10px 0 0}.key-grid{grid-template-columns:1fr}.risk-card ul{grid-template-columns:1fr}}
</style>
