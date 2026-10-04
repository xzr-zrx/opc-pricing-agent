<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  DataAnalysis,
  HomeFilled,
  Lightning,
  Monitor,
  Refresh,
  Setting,
  TrendCharts,
} from '@element-plus/icons-vue'
import { api } from './api/client'
import OverviewView from './views/OverviewView.vue'
import CompetitorView from './views/CompetitorView.vue'
import PriceTrendView from './views/PriceTrendView.vue'
import PricingAgentView from './views/PricingAgentView.vue'
import AuditView from './views/AuditView.vue'
import type {
  AgentRun,
  Competitor,
  MarketplacePayload,
  Product,
  Recommendation,
  TrendPayload,
  ViewKey,
} from './types'

const products = ref<Product[]>([])
const selectedId = ref<number | null>(null)
const competitors = ref<Competitor[]>([])
const recs = ref<Recommendation[]>([])
const runs = ref<AgentRun[]>([])
const marketplaceData = ref<MarketplacePayload | null>(null)
const trendData = ref<TrendPayload | null>(null)
const realTrendData = ref<TrendPayload | null>(null)
const activeView = ref<ViewKey>('overview')
const trendMode = ref<'real' | 'demo'>('real')
const busy = ref(false)
const marketplaceLoading = ref(false)
const trendLoading = ref(false)
const message = ref('')
type AlertType = 'success' | 'info' | 'warning' | 'error'
const messageType = ref<AlertType>('info')

function ymd(date: Date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
const today = new Date()
const sixDaysAgo = new Date(today)
sixDaysAgo.setDate(today.getDate() - 6)
const dateRange = ref<[string, string]>([ymd(sixDaysAgo), ymd(today)])

const selected = computed(() => products.value.find((item) => item.id === selectedId.value) || null)
const latestRun = computed(() => runs.value[0] || null)
const latestRecommendation = computed(() => recs.value[0] || null)

const grossMarginRate = computed(() => {
  if (!selected.value?.current_price) return 0
  return Math.round(((selected.value.current_price - selected.value.cost) / selected.value.current_price) * 100)
})
const minSafePrice = computed(() => {
  if (!selected.value) return 0
  return Math.round((selected.value.cost / (1 - selected.value.min_margin_rate)) * 100) / 100
})

const navItems: Array<{ key: ViewKey; label: string; icon: any; desc: string }> = [
  { key: 'overview', label: '总览', icon: HomeFilled, desc: '核心指标与摘要' },
  { key: 'competitors', label: '竞品监控', icon: Monitor, desc: '销量 Top15' },
  { key: 'trends', label: '价格趋势', icon: TrendCharts, desc: '最近7天波动' },
  { key: 'pricing', label: '定价建议', icon: DataAnalysis, desc: 'Agent 智能分析' },
  { key: 'audit', label: '运行审计', icon: Lightning, desc: '工具调用记录' },
]

function setMessage(text: string, type: AlertType = 'info') {
  message.value = text
  messageType.value = type
}
function humanError(error: any): string {
  const detail = error?.response?.data?.detail
  if (detail && typeof detail === 'object' && detail.message) return detail.message
  if (typeof detail === 'string') return detail
  if (error?.code === 'ECONNABORTED') return '请求超时，请稍后重试。'
  return error?.message || '请求失败，请稍后重试。'
}

async function loadProducts() {
  try {
    products.value = (await api.get('/products')).data
    if (!selectedId.value && products.value.length) selectedId.value = products.value[0].id
    if (selectedId.value) await loadDetail()
  } catch (error) {
    setMessage(`商品数据加载失败：${humanError(error)}`, 'error')
  }
}

async function loadTrend() {
  if (!selectedId.value) return
  trendLoading.value = true
  try {
    const params = { start_date: dateRange.value[0], end_date: dateRange.value[1] }
    realTrendData.value = (await api.get(`/products/${selectedId.value}/price-history`, {
      params: { ...params, mode: 'real' },
    })).data
    if (trendMode.value === 'real') {
      trendData.value = realTrendData.value
    } else {
      trendData.value = (await api.get(`/products/${selectedId.value}/price-history`, {
        params: { ...params, mode: 'demo' },
      })).data
    }
  } catch (error) {
    setMessage(`价格趋势加载失败：${humanError(error)}`, 'error')
  } finally {
    trendLoading.value = false
  }
}

async function loadDetail() {
  if (!selectedId.value) return
  const id = selectedId.value
  try {
    const [c, r, u, t] = await Promise.all([
      api.get(`/products/${id}/competitors`),
      api.get(`/products/${id}/recommendations`),
      api.get(`/products/${id}/runs`),
      api.get(`/products/${id}/competitors/marketplace/latest`),
    ])
    competitors.value = c.data
    recs.value = r.data
    runs.value = u.data
    marketplaceData.value = t.data
    await loadTrend()
  } catch (error) {
    setMessage(`当前商品数据加载失败：${humanError(error)}`, 'error')
  }
}

async function seed() {
  busy.value = true
  try {
    await api.post('/demo/seed')
    await loadProducts()
    setMessage('三个商品及明确标记的 Demo 基础数据已幂等补齐。', 'success')
  } catch (error) {
    setMessage(humanError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function searchMarketplace() {
  if (!selectedId.value || marketplaceLoading.value) return
  marketplaceLoading.value = true
  try {
    const response = await api.post(`/products/${selectedId.value}/competitors/search-marketplace`, null, { timeout: 30000 })
    marketplaceData.value = response.data
    trendMode.value = 'real'
    const suffix = response.data.notice ? ` ${response.data.notice}` : ''
    setMessage(`电商竞品查询完成，共展示 ${response.data.count} 条。${suffix}`, 'success')
    await loadDetail()
  } catch (error) {
    setMessage(humanError(error), 'error')
  } finally {
    marketplaceLoading.value = false
  }
}

async function analyze() {
  if (!selectedId.value) return
  busy.value = true
  try {
    await api.post(`/products/${selectedId.value}/analyze`, null, {
      params: { start_date: dateRange.value[0], end_date: dateRange.value[1] },
      timeout: 70000,
    })
    setMessage('Agent 已综合所选7天窗口与当前商品信息完成定价分析。', 'success')
    activeView.value = 'pricing'
    await loadDetail()
  } catch (error) {
    setMessage(`Agent 分析失败：${humanError(error)}`, 'error')
  } finally {
    busy.value = false
  }
}

async function testLLM() {
  busy.value = true
  try {
    const response = await api.post('/settings/llm/test')
    setMessage(response.data.ok ? `LLM 连接正常：${response.data.model}` : `LLM 连接失败：${response.data.error}`, response.data.ok ? 'success' : 'warning')
  } catch (error) {
    setMessage(humanError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function accept(id: number) {
  await api.post(`/recommendations/${id}/accept`)
  await loadDetail()
  setMessage('已标记为接受建议；系统不会自动修改真实售价。', 'success')
}
async function reject(id: number) {
  await api.post(`/recommendations/${id}/reject`)
  await loadDetail()
  setMessage('已标记为拒绝建议。', 'info')
}

function dateDiffInclusive(start: string, end: string) {
  const [sy, sm, sd] = start.split('-').map(Number)
  const [ey, em, ed] = end.split('-').map(Number)
  return Math.round((Date.UTC(ey, em - 1, ed) - Date.UTC(sy, sm - 1, sd)) / 86400000) + 1
}
async function handleRangeChange(range: [string, string]) {
  let [start, end] = range
  if (dateDiffInclusive(start, end) > 7) {
    const d = new Date(`${start}T00:00:00`)
    d.setDate(d.getDate() + 6)
    end = ymd(d)
    setMessage('单次最多查看7天，已自动调整为从开始日期起的7天范围。', 'warning')
  }
  dateRange.value = [start, end]
  await loadTrend()
}
async function handleModeChange(mode: 'real' | 'demo') {
  trendMode.value = mode
  await loadTrend()
}
function go(view: ViewKey) { activeView.value = view }

onMounted(loadProducts)
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true"><span></span><span></span></div>
        <div><strong>OPC Pricing Agent</strong><span>智能定价工作台</span></div>
      </div>

      <nav class="nav-list">
        <button v-for="item in navItems" :key="item.key" type="button" class="nav-item" :class="{ active: activeView === item.key }" @click="go(item.key)">
          <span class="nav-icon"><el-icon><component :is="item.icon" /></el-icon></span>
          <div><strong>{{ item.label }}</strong><span>{{ item.desc }}</span></div>
        </button>
      </nav>

      <div class="sidebar-spacer" />
      <div class="runtime-card">
        <div class="runtime-title"><span class="status-dot" />运行状态</div>
        <strong>{{ latestRun?.status || '等待运行' }}</strong>
        <span>{{ latestRun ? `${latestRun.provider} / ${latestRun.model}` : '暂无执行记录' }}</span>
      </div>
      <button class="sidebar-setting" type="button" @click="testLLM"><el-icon><Setting /></el-icon><span>连接测试</span></button>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="page-label">
          <span>{{ navItems.find(item => item.key === activeView)?.label }}</span>
          <b v-if="selected">{{ selected.name }}</b>
        </div>
        <div class="toolbar">
          <div class="product-picker">
            <el-select v-model="selectedId" class="product-select" placeholder="选择商品" @change="loadDetail">
              <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
            </el-select>
          </div>
          <el-button class="quiet-action" :icon="Refresh" :loading="busy" @click="seed">刷新基础数据</el-button>
          <el-button type="primary" :icon="Lightning" :loading="busy" @click="analyze">生成定价建议</el-button>
        </div>
      </header>

      <el-alert v-if="message" class="message-alert" :title="message" :type="messageType" show-icon closable @close="message = ''" />

      <div v-if="selected" class="page-host">
        <OverviewView
          v-if="activeView === 'overview'"
          :product="selected"
          :min-safe-price="minSafePrice"
          :gross-margin-rate="grossMarginRate"
          :marketplace="marketplaceData"
          :trend="realTrendData"
          :recommendation="latestRecommendation"
          :busy="busy"
          @navigate="go"
          @analyze="analyze"
          @search="searchMarketplace"
        />
        <CompetitorView v-else-if="activeView === 'competitors'" :product="selected" :marketplace="marketplaceData" :loading="marketplaceLoading" @search="searchMarketplace" />
        <PriceTrendView
          v-else-if="activeView === 'trends'"
          :product="selected"
          :trend="trendData"
          :date-range="dateRange"
          :mode="trendMode"
          :loading="trendLoading"
          @range-change="handleRangeChange"
          @mode-change="handleModeChange"
        />
        <PricingAgentView
          v-else-if="activeView === 'pricing'"
          :product="selected"
          :recommendation="latestRecommendation"
          :trend="realTrendData"
          :min-safe-price="minSafePrice"
          :gross-margin-rate="grossMarginRate"
          :busy="busy"
          @analyze="analyze"
          @accept="accept"
          @reject="reject"
        />
        <AuditView v-else :runs="runs" />
      </div>
      <div v-else class="loading-page">正在加载商品数据...</div>
    </main>
  </div>
</template>

<style>
:root {
  font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #25344f;
  background: #f4f7fb;
  font-synthesis: none;
  --page-bg: #f4f7fb;
  --card-bg: rgba(255,255,255,.96);
  --line: #e4eaf2;
  --line-soft: #eef2f7;
  --muted: #7b879a;
  --title: #10213d;
  --primary: #2f6df6;
  --primary-soft: #edf4ff;
  --success: #16a36f;
  --warning: #ef8b3a;
  --danger: #e45a68;
}
* { box-sizing: border-box; }
html, body, #app { width: 100%; height: 100%; margin: 0; overflow: hidden; }
body {
  min-width: 320px;
  background:
    radial-gradient(circle at 78% -8%, rgba(99,154,255,.16), transparent 30%),
    linear-gradient(180deg,#f8faff 0,#f3f6fb 100%);
}
button, input { font: inherit; }

.app-shell {
  height: 100vh;
  display: grid;
  grid-template-columns: 204px minmax(0, 1fr);
  overflow: hidden;
}
.sidebar {
  position: relative;
  z-index: 2;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 18px 13px 14px;
  border-right: 1px solid #e6ebf2;
  background: rgba(255,255,255,.92);
  backdrop-filter: blur(14px);
}
.brand { display:flex; align-items:center; gap:10px; padding:0 8px 16px; }
.brand-mark { position:relative; width:34px; height:34px; flex:0 0 auto; }
.brand-mark span { position:absolute; top:6px; width:21px; height:21px; border-radius:9px 12px 9px 12px; transform:rotate(45deg); }
.brand-mark span:first-child { left:1px; background:linear-gradient(135deg,#1e64f0,#6b7dff); }
.brand-mark span:last-child { right:1px; background:linear-gradient(135deg,#55a8ff,#77c9ff); opacity:.88; }
.brand strong,.brand span { display:block; }
.brand strong { color:#132340; font-size:14px; letter-spacing:-.015em; }
.brand>div:last-child>span { margin-top:2px; color:#97a1b0; font-size:10.5px; }
.nav-list { margin-top:8px; display:grid; gap:5px; }
.nav-item { width:100%; border:0; background:transparent; padding:9px 10px; border-radius:10px; display:flex; gap:10px; align-items:center; text-align:left; color:#62718a; cursor:pointer; transition:all .16s ease; }
.nav-item:hover { background:#f5f8fd; color:#2f6df6; }
.nav-item.active { color:#1f63e9; background:linear-gradient(90deg,#edf4ff,#f5f8ff); box-shadow:inset 0 0 0 1px #e5edff; }
.nav-icon { width:28px; height:28px; display:grid; place-items:center; flex:0 0 auto; border-radius:8px; color:#74829a; }
.nav-item.active .nav-icon { color:#2f6df6; background:#e7f0ff; }
.nav-item .el-icon { font-size:16px; }
.nav-item strong,.nav-item div>span { display:block; }
.nav-item strong { font-size:12.5px; font-weight:650; }
.nav-item div>span { margin-top:2px; color:#a0a9b7; font-size:10px; }
.nav-item.active div>span { color:#7896cf; }
.sidebar-spacer { flex:1; min-height:12px; }
.runtime-card { padding:10px 11px; border:1px solid #e5eaf1; border-radius:11px; background:linear-gradient(145deg,#fbfcfe,#f5f8fc); }
.runtime-title { display:flex; align-items:center; gap:6px; color:#7e8999; font-size:10.5px; }
.status-dot { width:7px; height:7px; border-radius:50%; background:#22b680; box-shadow:0 0 0 4px rgba(34,182,128,.08); }
.runtime-card strong,.runtime-card>span { display:block; }
.runtime-card strong { margin-top:6px; color:#30415a; font-size:12px; }
.runtime-card>span { margin-top:2px; color:#8d98a8; font-size:10px; word-break:break-word; line-height:1.35; }
.sidebar-setting { margin-top:6px; border:0; background:transparent; padding:8px 9px; border-radius:8px; display:flex; align-items:center; gap:7px; color:#718095; cursor:pointer; font-size:11.5px; }
.sidebar-setting:hover { background:#f3f7fc; color:#2f6df6; }

.main-panel {
  min-width:0;
  min-height:0;
  height:100%;
  display:flex;
  flex-direction:column;
  padding:0 16px 14px;
  overflow:hidden;
}
.topbar {
  flex:0 0 58px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  border-bottom:1px solid rgba(225,232,241,.78);
}
.page-label { min-width:0; display:flex; align-items:center; gap:10px; }
.page-label span { color:#2f6df6; font-size:13px; font-weight:700; }
.page-label b { max-width:360px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#8a96a8; font-size:11px; font-weight:500; }
.toolbar { display:flex; align-items:center; gap:7px; flex-wrap:nowrap; justify-content:flex-end; }
.product-select { width:228px; }
.message-alert { flex:0 0 auto; margin:8px 0 0; }
.page-host { flex:1 1 auto; min-width:0; min-height:0; padding-top:10px; overflow:hidden; }
.loading-page { height:100%; display:grid; place-items:center; color:#8490a0; font-size:12px; }

.el-button { min-height:32px; height:32px; padding:7px 12px !important; border-radius:8px !important; font-size:12px !important; }
.el-button--primary { border-color:#2f6df6 !important; background:#2f6df6 !important; box-shadow:0 6px 16px rgba(47,109,246,.12) !important; }
.el-button--success { box-shadow:none !important; }
.quiet-action { color:#65758e!important; border-color:#dfe6ef!important; background:rgba(255,255,255,.78)!important; }
.el-input__wrapper,.el-select__wrapper { min-height:33px!important; border-radius:8px!important; background:rgba(255,255,255,.92)!important; box-shadow:0 0 0 1px #dde5ef inset!important; }
.el-select__selected-item,.el-input__inner { font-size:12px!important; }
.el-alert { min-height:35px!important; padding:7px 10px!important; border-radius:9px!important; }
.el-alert__title { font-size:11.5px!important; }
.el-alert__icon { font-size:14px!important; }
.el-table { --el-table-border-color:#edf1f6; --el-table-header-bg-color:#f7f9fc; --el-table-tr-bg-color:#fff; --el-table-row-hover-bg-color:#f7faff; --el-table-text-color:#55657b; --el-table-header-text-color:#738095; font-size:11.5px!important; background:#fff!important; }
.el-table th.el-table__cell,.el-table td.el-table__cell { padding:6px 0!important; }
.el-table .cell { padding:0 8px!important; line-height:1.35!important; }
.el-collapse { border-top:0!important; border-bottom:0!important; }
.el-collapse-item__header { min-height:48px!important; height:auto!important; border-bottom:1px solid #edf1f5!important; background:transparent!important; }
.el-collapse-item__wrap { background:transparent!important; border-bottom:1px solid #edf1f5!important; }
.el-radio-button__inner { padding:8px 12px!important; font-size:11.5px!important; }
.el-date-editor { min-width:280px; min-height:33px!important; }
.el-tag { font-size:10.5px!important; border-radius:7px!important; }

.ui-scroll { scrollbar-width:thin; scrollbar-color:#cbd7e7 transparent; }
.ui-scroll::-webkit-scrollbar { width:5px; height:5px; }
.ui-scroll::-webkit-scrollbar-track { background:transparent; }
.ui-scroll::-webkit-scrollbar-thumb { background:#cbd7e7; border-radius:999px; }
.ui-scroll::-webkit-scrollbar-thumb:hover { background:#afbdd1; }

@media (max-height: 800px) and (min-width: 981px) {
  .sidebar { padding-top:13px; }
  .brand { padding-bottom:11px; }
  .brand>div:last-child>span,.nav-item div>span,.runtime-card>span { display:none; }
  .nav-item { padding:7px 9px; }
  .topbar { flex-basis:52px; }
  .page-host { padding-top:8px; }
}
@media(max-width:980px){
  html,body,#app{height:auto;min-height:100%;overflow:auto}
  .app-shell{height:auto;min-height:100vh;grid-template-columns:1fr;overflow:visible}
  .sidebar{height:auto;position:static;flex-direction:row;align-items:center;overflow-x:auto;border-right:0;border-bottom:1px solid #e7ecf3;padding:8px 10px}
  .brand{padding:0 12px 0 0;flex:0 0 auto}.brand>div:last-child>span,.runtime-card,.sidebar-setting,.sidebar-spacer{display:none}
  .nav-list{margin:0;display:flex;gap:4px}.nav-item{flex:0 0 auto;width:auto}.nav-item div>span{display:none}
  .main-panel{height:auto;padding:0 10px 12px;overflow:visible}.page-host{overflow:visible}.topbar{min-height:58px;flex-wrap:wrap;height:auto;padding:8px 0}.toolbar{flex-wrap:wrap}.page-label b{display:none}
}
@media(max-width:680px){.toolbar{align-items:stretch;width:100%}.product-picker,.product-select{width:100%}.quiet-action{display:none}.brand div:last-child{display:none}.el-date-editor{min-width:100%}}
</style>
