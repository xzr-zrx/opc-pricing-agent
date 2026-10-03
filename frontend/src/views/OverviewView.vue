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
      <MetricCard label="最低安全价" :value="`¥${minSafePrice}`" :note="`成本 ¥${product.cost} · 当前毛利 ${grossMarginRate}%`" :icon="TrendCharts" />
      <MetricCard label="可用库存" :value="product.stock" note="系统当前库存" :icon="Box" />
      <MetricCard label="当前竞品" :value="marketplace?.count || 0" note="最近一次销量 Top5" :icon="Monitor" />
    </section>

    <section class="overview-grid">
      <article class="surface-card trend-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">MARKET TREND</span>
            <h2>最近7天价格走势</h2>
            <p>{{ trend?.source_label || '暂无趋势数据' }}</p>
          </div>
          <el-button text @click="emit('navigate', 'trends')">查看完整趋势 →</el-button>
        </div>
        <PriceTrendChart :trend="trend" :height="280" compact />
        <div v-if="trend?.notice" class="inline-note" :class="{ warning: trend.history_insufficient }">
          {{ trend.notice }}
        </div>
      </article>

      <article class="surface-card agent-summary-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">AGENT DECISION</span>
            <h2>最新定价建议</h2>
            <p>基于最近7天真实趋势与当前竞品数据</p>
          </div>
          <el-button text @click="emit('navigate', 'pricing')">查看完整建议 →</el-button>
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
            <div><span>数据完整度</span><strong>{{ recommendation.data_completeness }}</strong></div>
            <div><span>置信度</span><strong>{{ recommendation.confidence != null ? `${Math.round(recommendation.confidence * 100)}%` : '—' }}</strong></div>
            <div><span>风险等级</span><strong>{{ recommendation.risk_level || '—' }}</strong></div>
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
      <div class="section-head">
        <div>
          <span class="section-kicker">LATEST COMPETITORS</span>
          <h2>最新竞品摘要</h2>
          <p>仅展示最近一次查询的前三名</p>
        </div>
        <div class="head-actions">
          <el-button @click="emit('search')">查询竞品</el-button>
          <el-button type="primary" @click="emit('navigate', 'competitors')">查看完整竞品</el-button>
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
.page-stack { display: grid; gap: 18px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.overview-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(320px, .8fr); gap: 18px; }
.surface-card { border: 1px solid #dfe7f1; background: rgba(255,255,255,.92); border-radius: 20px; box-shadow: 0 12px 34px rgba(39,65,102,.06); padding: 22px; }
.section-head { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; }
.section-kicker { color: #5b79c8; font-size: 11px; font-weight: 800; letter-spacing: .14em; }
h2 { margin: 5px 0 4px; color: #192842; font-size: 20px; }
.section-head p { margin: 0; color: #8a97aa; font-size: 13px; }
.inline-note { margin-top: 8px; padding: 10px 12px; border-radius: 12px; background: #eef7f4; color: #4f776b; font-size: 12px; line-height: 1.5; }
.inline-note.warning { background: #fff7e9; color: #8a6a2f; }
.decision-hero { margin-top: 18px; display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; padding: 18px; border-radius: 16px; background: linear-gradient(135deg, #eff5ff, #f7fbff); border: 1px solid #e0e8f7; }
.decision-hero span, .decision-hero strong { display: block; }
.decision-hero span { color: #75859b; font-size: 12px; }
.decision-hero strong { margin-top: 4px; color: #1e3153; font-size: 32px; }
.decision-summary { color: #5e6c80; font-size: 14px; line-height: 1.7; margin: 18px 0; }
.decision-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.decision-meta div { padding: 12px; border-radius: 14px; background: #f6f8fb; }
.decision-meta span, .decision-meta strong { display: block; }
.decision-meta span { color: #8c98a9; font-size: 11px; }
.decision-meta strong { margin-top: 4px; color: #2b3a52; font-size: 14px; }
.empty-block { min-height: 260px; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 8px; text-align: center; color: #8f9bae; }
.empty-block strong { color: #4e5e76; font-size: 15px; }
.empty-block span { font-size: 13px; }
.head-actions { display: flex; gap: 8px; }
.top3-grid { margin-top: 16px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.mini-product { min-width: 0; display: flex; gap: 12px; padding: 13px; border-radius: 15px; background: #f7f9fc; border: 1px solid #e6ebf2; }
.mini-product img { width: 52px; height: 52px; border-radius: 12px; object-fit: cover; flex: 0 0 auto; }
.mini-product div { min-width: 0; }
.mini-product strong, .mini-product span, .mini-product small { display: block; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.mini-product strong { color: #283750; font-size: 13px; }
.mini-product span { margin-top: 6px; color: #4968a8; font-size: 12px; }
.mini-product small { margin-top: 3px; color: #98a3b2; font-size: 11px; }
.empty-inline { margin-top: 16px; padding: 28px; text-align: center; color: #98a3b1; background: #f7f9fc; border-radius: 14px; font-size: 13px; }
@media (max-width: 1180px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } .overview-grid { grid-template-columns: 1fr; } }
@media (max-width: 720px) { .metric-grid, .top3-grid { grid-template-columns: 1fr; } .surface-card { padding: 16px; } .section-head { flex-direction: column; } }
</style>
