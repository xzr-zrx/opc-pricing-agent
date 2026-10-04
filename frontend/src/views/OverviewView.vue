<script setup lang="ts">
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

function strategyLabel() {
  return props.recommendation?.strategy || props.recommendation?.promotion?.strategy || '等待分析'
}
</script>

<template>
  <div class="page-stack">
    <section class="metric-grid">
      <MetricCard label="当前售价" :value="`¥${product.current_price}`" note="当前挂牌价" :icon="Money" />
      <MetricCard label="最低安全价" :value="`¥${minSafePrice}`" :note="`成本 ¥${product.cost} · 毛利 ${grossMarginRate}%`" :icon="TrendCharts" />
      <MetricCard label="可用库存" :value="product.stock" note="当前库存" :icon="Box" />
      <MetricCard label="当前竞品" :value="marketplace?.count || 0" note="最近一次销量 Top15" :icon="Monitor" />
    </section>

    <section class="overview-grid">
      <article class="surface-card trend-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">MARKET TREND</span>
            <h2>最近7天价格走势</h2>
            <p>{{ trend?.source_label || '暂无趋势数据' }}</p>
          </div>
          <el-button text @click="emit('navigate', 'trends')">完整趋势 →</el-button>
        </div>
        <PriceTrendChart :trend="trend" :height="210" compact />
        <div v-if="trend?.notice" class="inline-note" :class="{ warning: trend.history_insufficient }">
          {{ trend.notice }}
        </div>
      </article>

      <article class="surface-card agent-summary-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">AGENT DECISION</span>
            <h2>最新定价建议</h2>
            <p>综合7天趋势与前15个竞品</p>
          </div>
          <el-button text @click="emit('navigate', 'pricing')">完整建议 →</el-button>
        </div>

        <template v-if="recommendation">
          <div class="decision-hero">
            <div>
              <span>建议价格</span>
              <strong>¥{{ recommendation.suggested_price ?? product.current_price }}</strong>
            </div>
            <el-tag effect="light" round>{{ strategyLabel() }}</el-tag>
          </div>
          <p class="decision-summary">{{ recommendation.summary || recommendation.promotion?.summary || '已生成定价建议，请进入定价建议页查看完整理由。' }}</p>
          <div class="decision-meta">
            <div><span>完整度</span><strong>{{ recommendation.data_completeness }}</strong></div>
            <div><span>置信度</span><strong>{{ recommendation.confidence != null ? `${Math.round(recommendation.confidence * 100)}%` : '—' }}</strong></div>
            <div><span>风险</span><strong>{{ recommendation.risk_level || '—' }}</strong></div>
          </div>
        </template>
        <div v-else class="empty-block">
          <strong>尚未生成定价建议</strong>
          <span>先查询竞品，再运行 Agent 分析。</span>
          <el-button type="primary" :loading="busy" @click="emit('analyze')">开始 Agent 分析</el-button>
        </div>
      </article>
    </section>

    <section class="surface-card top3-card">
      <div class="section-head compact-head">
        <div>
          <span class="section-kicker">LATEST COMPETITORS</span>
          <h2>最新竞品摘要</h2>
        </div>
        <div class="head-actions">
          <el-button @click="emit('search')">查询竞品</el-button>
          <el-button type="primary" @click="emit('navigate', 'competitors')">完整竞品</el-button>
        </div>
      </div>
      <div v-if="marketplace?.items?.length" class="top3-grid">
        <article v-for="item in marketplace.items.slice(0, 3)" :key="item.competitor_id" class="mini-product">
          <img v-if="item.image_url" :src="item.image_url" alt="" />
          <div>
            <strong>{{ item.title }}</strong>
            <span>¥{{ item.price }} · 销量 {{ item.sales_text }}</span>
            <small>{{ item.shop_name || '未知店铺' }}</small>
          </div>
        </article>
      </div>
      <div v-else class="empty-inline">暂无实时竞品数据，请先执行一次电商竞品查询。</div>
    </section>
  </div>
</template>

<style scoped>
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto minmax(0,1fr) auto; gap:8px; }
.metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; }
.overview-grid { min-height:0; display:grid; grid-template-columns:minmax(0,1.55fr) minmax(300px,.75fr); gap:8px; }
.surface-card { min-height:0; border:1px solid #dfe6ee; background:#fff; border-radius:11px; padding:12px 14px; overflow:hidden; }
.section-head { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
.section-kicker { color:#6178a2; font-size:11px; font-weight:700; }
h2 { margin:2px 0; color:#1c2b3f; font-size:16px; line-height:1.2; }
.section-head p { margin:0; color:#7f8b9a; font-size:11px; }
.inline-note { margin-top:4px; padding:6px 8px; border-radius:7px; background:#eef8f4; color:#4f7468; font-size:10.5px; line-height:1.35; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.inline-note.warning { background:#fff6e8; color:#86662e; }
.decision-hero { margin-top:9px; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 11px; border-radius:9px; background:#f5f8fd; border:1px solid #e0e7f0; }
.decision-hero span,.decision-hero strong { display:block; }
.decision-hero span { color:#748195; font-size:11px; }
.decision-hero strong { margin-top:2px; color:#2457bd; font-size:25px; line-height:1; letter-spacing:-.03em; }
.decision-summary { color:#596a80; font-size:12px; line-height:1.45; margin:9px 0; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.decision-meta { display:grid; grid-template-columns:repeat(3,1fr); gap:7px; }
.decision-meta div { padding:7px 8px; border-radius:8px; background:#f8fafc; border:1px solid #e6ebf1; }
.decision-meta span,.decision-meta strong { display:block; }
.decision-meta span { color:#7f8b9a; font-size:10.5px; }
.decision-meta strong { margin-top:2px; color:#2b3b52; font-size:12px; }
.empty-block { height:calc(100% - 42px); min-height:150px; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:6px; text-align:center; color:#8793a3; }
.empty-block strong { color:#4e5e76; font-size:14px; }
.empty-block span { font-size:11px; }
.head-actions { display:flex; gap:6px; }
.top3-card { padding-top:10px; padding-bottom:10px; }
.compact-head { align-items:center; }
.compact-head h2 { margin-bottom:0; }
.top3-grid { margin-top:7px; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:7px; }
.mini-product { min-width:0; display:flex; gap:8px; padding:8px; border-radius:8px; background:#f8fafc; border:1px solid #e5eaf0; }
.mini-product img { width:40px; height:40px; border-radius:6px; object-fit:cover; flex:0 0 auto; }
.mini-product div { min-width:0; }
.mini-product strong,.mini-product span,.mini-product small { display:block; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.mini-product strong { color:#2a3951; font-size:12px; }
.mini-product span { margin-top:3px; color:#4968a8; font-size:11px; }
.mini-product small { margin-top:1px; color:#8f9aa8; font-size:10.5px; }
.empty-inline { margin-top:8px; padding:13px; text-align:center; color:#8c97a6; background:#f8fafc; border-radius:8px; font-size:11px; }
@media(max-height:800px) and (min-width:981px){.surface-card{padding:10px 12px}.metric-grid{gap:7px}.overview-grid{gap:7px}}
@media(max-width:1180px){.overview-grid{grid-template-columns:1fr 330px}.metric-grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.overview-grid{grid-template-columns:1fr}.metric-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){.metric-grid,.top3-grid{grid-template-columns:1fr}.surface-card{padding:12px}.section-head{flex-direction:column}}
</style>
