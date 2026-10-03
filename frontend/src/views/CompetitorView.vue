<script setup lang="ts">
import { computed } from 'vue'
import { Link, Search } from '@element-plus/icons-vue'
import type { MarketplacePayload, Product } from '../types'

const props = defineProps<{
  product: Product
  marketplace: MarketplacePayload | null
  loading: boolean
}>()
const emit = defineEmits<{ search: [] }>()

const stats = computed(() => {
  const items = props.marketplace?.items || []
  const prices = items.map((item) => Number(item.price)).filter(Number.isFinite).sort((a,b) => a-b)
  if (!prices.length) return { avg: null, min: null, max: null, median: null, totalSales: 0 }
  const mid = Math.floor(prices.length / 2)
  const median = prices.length % 2 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2
  return {
    avg: prices.reduce((a,b) => a+b, 0) / prices.length,
    min: prices[0],
    max: prices[prices.length - 1],
    median,
    totalSales: items.reduce((sum, item) => sum + Number(item.sales || 0), 0),
  }
})

function fmt(value: number | null) { return value == null ? '—' : `¥${value.toFixed(2)}` }
function formatTime(value?: string | null) {
  if (!value) return '尚未查询'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="page-stack">
    <section class="hero-card">
      <div>
        <span class="kicker">COMPETITOR MONITORING</span>
        <h2>竞品监控</h2>
        <p>当前商品：{{ product.name }} · 搜索词：{{ marketplace?.keyword || product.search_keyword || product.name }}</p>
      </div>
      <div class="hero-actions">
        <div class="source-chip">拼多多 · 多多进宝</div>
        <el-button type="primary" :icon="Search" :loading="loading" @click="emit('search')">{{ loading ? '正在查询...' : '查询电商竞品' }}</el-button>
      </div>
    </section>

    <section class="stats-grid">
      <article><span>Top5 平均价</span><strong>{{ fmt(stats.avg) }}</strong></article>
      <article><span>最低价</span><strong>{{ fmt(stats.min) }}</strong></article>
      <article><span>最高价</span><strong>{{ fmt(stats.max) }}</strong></article>
      <article><span>中位价</span><strong>{{ fmt(stats.median) }}</strong></article>
      <article><span>销量参考合计</span><strong>{{ stats.totalSales ? stats.totalSales.toLocaleString() : '—' }}</strong></article>
    </section>

    <section class="surface-card table-card">
      <div class="section-head">
        <div>
          <span class="kicker">TOP 5 RESULTS</span>
          <h3>本次查询结果</h3>
          <p>最近查询：{{ formatTime(marketplace?.queried_at) }}</p>
        </div>
        <span class="soft-note">最多展示5条</span>
      </div>

      <el-table v-if="marketplace?.items?.length" :data="marketplace.items" class="market-table">
        <el-table-column prop="rank" label="排名" width="70" align="center" />
        <el-table-column label="商品" min-width="300">
          <template #default="scope">
            <div class="product-cell">
              <img v-if="scope.row.image_url" :src="scope.row.image_url" alt="" />
              <div><strong>{{ scope.row.title }}</strong><small>{{ scope.row.shop_name || '未知店铺' }}</small></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="120"><template #default="scope"><b class="price">¥{{ scope.row.price }}</b></template></el-table-column>
        <el-table-column label="销量" width="140"><template #default="scope">{{ scope.row.sales_text }}</template></el-table-column>
        <el-table-column prop="shop_name" label="店铺" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="90" align="center">
          <template #default="scope">
            <a v-if="scope.row.url" class="link" :href="scope.row.url" target="_blank" rel="noopener noreferrer"><el-icon><Link /></el-icon>查看</a>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-block">
        <el-icon><Search /></el-icon>
        <strong>暂无实时竞品数据</strong>
        <span>点击“查询电商竞品”获取当前商品的拼多多公开数据。</span>
      </div>
      <div class="footer-note">{{ marketplace?.notice || 'Top5 仅代表本次搜索结果中成功获得销量数据的商品，不代表拼多多全平台绝对销量前5。' }}</div>
    </section>
  </div>
</template>

<style scoped>
.page-stack { display: grid; gap: 18px; }
.hero-card, .surface-card { border: 1px solid #dfe7f1; background: rgba(255,255,255,.92); border-radius: 20px; box-shadow: 0 12px 34px rgba(39,65,102,.06); }
.hero-card { padding: 22px 24px; display: flex; align-items: center; justify-content: space-between; gap: 20px; }
.kicker { color: #5c79c6; font-size: 11px; font-weight: 800; letter-spacing: .14em; }
h2 { margin: 5px 0; color: #182741; font-size: 26px; } .hero-card p { margin: 0; color: #8491a4; font-size: 13px; }
.hero-actions { display: flex; align-items: center; gap: 10px; }
.source-chip, .soft-note { border: 1px solid #dce5f2; background: #f6f9fd; color: #61718a; border-radius: 999px; padding: 8px 12px; font-size: 12px; }
.stats-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.stats-grid article { padding: 16px 18px; border-radius: 16px; background: rgba(255,255,255,.9); border: 1px solid #e0e7f0; box-shadow: 0 8px 24px rgba(39,65,102,.045); }
.stats-grid span, .stats-grid strong { display: block; } .stats-grid span { color: #8793a5; font-size: 12px; } .stats-grid strong { margin-top: 6px; color: #243650; font-size: 21px; }
.surface-card { padding: 22px; }
.section-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }
h3 { margin: 5px 0; color: #1f2f49; font-size: 20px; }.section-head p { margin: 0; color: #909cad; font-size: 12px; }
.product-cell { display: flex; align-items: center; gap: 12px; min-width: 0; }.product-cell img { width: 48px; height: 48px; border-radius: 12px; object-fit: cover; border: 1px solid #e5ebf3; }.product-cell div { min-width: 0; }.product-cell strong,.product-cell small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.product-cell strong { color: #2c3b53; font-size: 13px; }.product-cell small { margin-top: 5px; color: #98a3b2; font-size: 11px; }
.price { color: #315fc8; }.link { color: #386bd3; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }.empty-block { min-height: 280px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #929eae; }.empty-block .el-icon { font-size: 30px; color: #aab8ca; }.empty-block strong { color: #596980; font-size: 15px; }.empty-block span { font-size: 13px; }.footer-note { margin-top: 14px; color: #909bab; font-size: 12px; line-height: 1.6; }
@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(2,1fr)}.hero-card{align-items:flex-start;flex-direction:column}}@media(max-width:680px){.stats-grid{grid-template-columns:1fr}.hero-actions{width:100%;flex-wrap:wrap}}
</style>
