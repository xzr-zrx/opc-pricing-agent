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
        <p>{{ product.name }} · 搜索词：{{ marketplace?.keyword || product.search_keyword || product.name }}</p>
      </div>
      <div class="hero-actions">
        <div class="source-chip">拼多多 · 多多进宝</div>
        <el-button type="primary" :icon="Search" :loading="loading" @click="emit('search')">{{ loading ? '正在查询...' : '查询电商竞品' }}</el-button>
      </div>
    </section>

    <section class="stats-grid">
      <article><span>Top5 均价</span><strong>{{ fmt(stats.avg) }}</strong></article>
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

      <el-table v-if="marketplace?.items?.length" :data="marketplace.items" class="market-table" size="small">
        <el-table-column prop="rank" label="#" width="50" align="center" />
        <el-table-column label="商品" min-width="300">
          <template #default="scope">
            <div class="product-cell">
              <img v-if="scope.row.image_url" :src="scope.row.image_url" alt="" />
              <div><strong>{{ scope.row.title }}</strong><small>{{ scope.row.shop_name || '未知店铺' }}</small></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="100"><template #default="scope"><b class="price">¥{{ scope.row.price }}</b></template></el-table-column>
        <el-table-column label="销量" width="110"><template #default="scope">{{ scope.row.sales_text }}</template></el-table-column>
        <el-table-column prop="shop_name" label="店铺" min-width="130" show-overflow-tooltip />
        <el-table-column label="操作" width="70" align="center">
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
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto auto minmax(0,1fr); gap:10px; }
.hero-card,.surface-card { border:1px solid rgba(218,228,241,.96); background:linear-gradient(145deg,rgba(253,254,255,.96),rgba(246,249,253,.94)); border-radius:16px; box-shadow:0 9px 24px rgba(42,72,110,.055), inset 0 1px 0 rgba(255,255,255,.86); }
.hero-card { padding:12px 16px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#5d79c5; font-size:9px; font-weight:800; letter-spacing:.13em; }
h2 { margin:3px 0 2px; color:#182741; font-size:18px; line-height:1.2; }
.hero-card p { margin:0; color:#8794a7; font-size:10px; }
.hero-actions { display:flex; align-items:center; gap:7px; }
.source-chip,.soft-note { border:1px solid #dce6f1; background:#f4f8fc; color:#61718a; border-radius:999px; padding:6px 9px; font-size:10px; }
.stats-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; }
.stats-grid article { padding:10px 12px; border-radius:13px; background:linear-gradient(145deg,rgba(253,254,255,.95),rgba(246,249,253,.92)); border:1px solid #dfe8f2; box-shadow:0 6px 17px rgba(39,65,102,.04); }
.stats-grid span,.stats-grid strong { display:block; }
.stats-grid span { color:#8793a5; font-size:10px; }
.stats-grid strong { margin-top:3px; color:#243650; font-size:17px; line-height:1.05; }
.surface-card { min-height:0; padding:12px 15px 9px; display:flex; flex-direction:column; overflow:hidden; }
.section-head { flex:0 0 auto; display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:7px; }
h3 { margin:2px 0; color:#1f2f49; font-size:15px; }
.section-head p { margin:0; color:#909cad; font-size:9.5px; }
.market-table { flex:1 1 auto; min-height:0; }
.product-cell { display:flex; align-items:center; gap:8px; min-width:0; }
.product-cell img { width:34px; height:34px; border-radius:8px; object-fit:cover; border:1px solid #e3ebf4; }
.product-cell div { min-width:0; }
.product-cell strong,.product-cell small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.product-cell strong { color:#2c3b53; font-size:10.5px; }
.product-cell small { margin-top:2px; color:#98a3b2; font-size:9px; }
.price { color:#315fc8; font-size:11px; }
.link { color:#386bd3; text-decoration:none; display:inline-flex; align-items:center; gap:3px; font-size:10px; }
.empty-block { flex:1; min-height:180px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; color:#929eae; }
.empty-block .el-icon { font-size:24px; color:#aab8ca; }
.empty-block strong { color:#596980; font-size:13px; }
.empty-block span { font-size:10px; }
.footer-note { flex:0 0 auto; margin-top:6px; padding-top:6px; border-top:1px solid #e8eef4; color:#909bab; font-size:9px; line-height:1.35; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(5,1fr)}.hero-card{align-items:center}}
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.stats-grid{grid-template-columns:repeat(2,1fr)}.hero-card{align-items:flex-start;flex-direction:column}.surface-card{overflow:visible}}
@media(max-width:680px){.stats-grid{grid-template-columns:1fr}.hero-actions{width:100%;flex-wrap:wrap}}
</style>
