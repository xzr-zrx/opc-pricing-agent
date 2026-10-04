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

const displayedItems = computed(() => (props.marketplace?.items || []).slice(0, 15))
const stats = computed(() => {
  const items = displayedItems.value
  const prices = items.map((item) => Number(item.price)).filter(Number.isFinite).sort((a, b) => a - b)
  if (!prices.length) return { count: 0, avg: null, min: null, max: null, median: null, totalSales: 0 }
  const mid = Math.floor(prices.length / 2)
  const median = prices.length % 2 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2
  return {
    count: items.length,
    avg: prices.reduce((a, b) => a + b, 0) / prices.length,
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
        <span class="kicker">竞品数据</span>
        <h2>竞品监控</h2>
        <p>{{ product.name }} · 搜索词：{{ marketplace?.keyword || product.search_keyword || product.name }}</p>
      </div>
      <div class="hero-actions">
        <div class="source-chip">{{ marketplace?.provider_name || '拼多多 · 多多进宝' }}</div>
        <el-button type="primary" :icon="Search" :loading="loading" @click="emit('search')">{{ loading ? '正在查询...' : '查询前15个竞品' }}</el-button>
      </div>
    </section>

    <section class="stats-grid">
      <article><span>Top15 竞品均价</span><strong>{{ fmt(stats.avg) }}</strong><small>{{ stats.count }}/15 个有效样本</small></article>
      <article><span>最低价</span><strong>{{ fmt(stats.min) }}</strong><small>当前样本最低</small></article>
      <article><span>最高价</span><strong>{{ fmt(stats.max) }}</strong><small>当前样本最高</small></article>
      <article><span>中位价</span><strong>{{ fmt(stats.median) }}</strong><small>降低极端价格影响</small></article>
      <article><span>销量参考总量</span><strong>{{ stats.count ? stats.totalSales.toLocaleString() : '—' }}</strong><small>按当前平台口径汇总</small></article>
    </section>

    <section class="surface-card table-card">
      <div class="section-head">
        <div>
          <span class="kicker">查询结果</span>
          <h3>销量排名前 15 个有效竞品</h3>
          <p>最近查询：{{ formatTime(marketplace?.queried_at) }}</p>
        </div>
        <span class="soft-note">卡片内滚动 · 表头固定</span>
      </div>

      <div v-if="displayedItems.length" class="table-shell">
        <el-table :data="displayedItems" height="100%" class="market-table" size="small">
          <el-table-column prop="rank" label="#" width="52" align="center" fixed />
          <el-table-column label="商品" min-width="320">
            <template #default="scope">
              <div class="product-cell">
                <img v-if="scope.row.image_url" :src="scope.row.image_url" alt="" />
                <div><strong>{{ scope.row.title }}</strong><small>{{ scope.row.shop_name || '未知店铺' }}</small></div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="价格" width="108"><template #default="scope"><b class="price">¥{{ Number(scope.row.price).toFixed(2) }}</b></template></el-table-column>
          <el-table-column label="销量参考" width="130"><template #default="scope">{{ scope.row.sales_text || scope.row.sales }}</template></el-table-column>
          <el-table-column prop="shop_name" label="店铺" min-width="145" show-overflow-tooltip />
          <el-table-column label="商品链接" width="92" align="center" fixed="right">
            <template #default="scope">
              <a v-if="scope.row.url" class="link" :href="scope.row.url" target="_blank" rel="noopener noreferrer"><el-icon><Link /></el-icon>查看</a>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else class="empty-block">
        <el-icon><Search /></el-icon>
        <strong>暂无实时竞品数据</strong>
        <span>点击“查询前15个竞品”获取当前商品的公开市场数据。</span>
      </div>
      <div class="footer-note">{{ marketplace?.notice || 'Top15 仅代表本次搜索结果中成功获得有效价格和销量参考的商品，不代表全平台绝对销量前15。' }}</div>
    </section>
  </div>
</template>

<style scoped>
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto auto minmax(0,1fr); gap:8px; }
.hero-card,.surface-card { border:1px solid #dfe6ee; background:#fff; border-radius:11px; }
.hero-card { padding:10px 14px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#6178a2; font-size:11px; font-weight:700; }
h2 { margin:2px 0; color:#1c2b3f; font-size:18px; line-height:1.2; }
.hero-card p { margin:0; color:#7f8b9a; font-size:11px; }
.hero-actions { display:flex; align-items:center; gap:7px; }
.source-chip,.soft-note { border:1px solid #dfe6ee; background:#f7f9fc; color:#647286; border-radius:7px; padding:6px 9px; font-size:11px; white-space:nowrap; }
.stats-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }
.stats-grid article { padding:9px 11px; border-radius:10px; background:#fff; border:1px solid #dfe6ee; }
.stats-grid span,.stats-grid strong,.stats-grid small { display:block; }
.stats-grid span { color:#7d8998; font-size:11px; }
.stats-grid strong { margin-top:3px; color:#22344d; font-size:17px; line-height:1.05; }
.stats-grid small { margin-top:3px; color:#9aa4b1; font-size:10.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.surface-card { min-height:0; padding:10px 12px 8px; display:flex; flex-direction:column; overflow:hidden; }
.section-head { flex:0 0 auto; display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:7px; }
h3 { margin:2px 0; color:#223149; font-size:16px; }
.section-head p { margin:0; color:#8b96a4; font-size:11px; }
.table-shell { flex:1 1 auto; min-height:0; overflow:hidden; border:1px solid #e6ebf1; border-radius:8px; }
.market-table { width:100%; height:100%; }
.product-cell { display:flex; align-items:center; gap:9px; min-width:0; }
.product-cell img { width:38px; height:38px; border-radius:6px; object-fit:cover; border:1px solid #e5ebf1; background:#f5f7fa; }
.product-cell div { min-width:0; }
.product-cell strong,.product-cell small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.product-cell strong { color:#2c3b50; font-size:12px; font-weight:650; }
.product-cell small { margin-top:2px; color:#8c97a5; font-size:11px; }
.price { color:#2e61c7; font-size:12.5px; }
.link { color:#3568d4; text-decoration:none; display:inline-flex; align-items:center; gap:3px; font-size:12px; }
.muted { color:#a0a9b5; }
.empty-block { flex:1; min-height:180px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; color:#8c97a5; }
.empty-block .el-icon { font-size:24px; color:#a7b1be; }
.empty-block strong { color:#56657a; font-size:14px; }
.empty-block span { font-size:12px; }
.footer-note { flex:0 0 auto; margin-top:6px; padding-top:6px; border-top:1px solid #edf1f5; color:#8894a3; font-size:10.5px; line-height:1.35; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
:deep(.el-scrollbar__bar.is-vertical) { width:7px; }
:deep(.el-scrollbar__thumb) { background:#b8c4d2; opacity:.55; }
@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(5,1fr)}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.stats-grid{grid-template-columns:repeat(2,1fr)}.hero-card{align-items:flex-start;flex-direction:column}.surface-card{overflow:visible}.table-shell{height:520px;flex:none}}
@media(max-width:680px){.stats-grid{grid-template-columns:1fr}.hero-actions{width:100%;flex-wrap:wrap}.soft-note{display:none}}
</style>
