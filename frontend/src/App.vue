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
  { key: 'competitors', label: '竞品监控', icon: Monitor, desc: '拼多多 Top5' },
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
        <div class="brand-mark">OP</div>
        <div><strong>OPC Agent</strong><span>Pricing Console</span></div>
      </div>

      <nav class="nav-list">
        <button v-for="item in navItems" :key="item.key" type="button" class="nav-item" :class="{ active: activeView === item.key }" @click="go(item.key)">
          <el-icon><component :is="item.icon" /></el-icon>
          <div><strong>{{ item.label }}</strong><span>{{ item.desc }}</span></div>
        </button>
      </nav>

      <div class="sidebar-spacer" />
      <div class="runtime-card">
        <div class="runtime-title"><span class="status-dot" />Agent Runtime</div>
        <strong>{{ latestRun?.status || '等待运行' }}</strong>
        <span>{{ latestRun ? `${latestRun.provider} / ${latestRun.model}` : '暂无执行记录' }}</span>
      </div>
      <button class="sidebar-setting" type="button" @click="testLLM"><el-icon><Setting /></el-icon><span>连接测试</span></button>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="title-group">
          <span class="eyebrow">SMART PRICING WORKSPACE</span>
          <h1>竞品监测与智能定价</h1>
          <p>功能按页面切换，真实竞品先入库，再由 Agent 后端工具读取并决策。</p>
        </div>
        <div class="toolbar">
          <div class="product-picker">
            <span>当前商品</span>
            <el-select v-model="selectedId" class="product-select" placeholder="选择商品" @change="loadDetail">
              <el-option v-for="product in products" :key="product.id" :label="product.name" :value="product.id" />
            </el-select>
          </div>
          <el-button :icon="Refresh" :loading="busy" @click="seed">补齐 Demo 数据</el-button>
          <el-button type="primary" :icon="Lightning" :loading="busy" @click="analyze">Agent 定价分析</el-button>
        </div>
      </header>

      <div class="context-strip">
        <span>{{ navItems.find(item => item.key === activeView)?.label }}</span>
        <b v-if="selected">{{ selected.name }}</b>
        <em>分析窗口 {{ dateRange[0] }} ~ {{ dateRange[1] }}</em>
      </div>

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
  color: #20304a;
  background: #eef3f8;
  font-synthesis: none;
}
* { box-sizing: border-box; }
html, body, #app { min-height: 100%; margin: 0; }
body {
  min-width: 320px;
  background:
    radial-gradient(circle at 88% 8%, rgba(111, 151, 230, .12), transparent 28%),
    radial-gradient(circle at 15% 100%, rgba(74, 186, 159, .08), transparent 30%),
    #eef3f8;
}
button, input { font: inherit; }

.app-shell { min-height: 100vh; display: grid; grid-template-columns: 236px minmax(0, 1fr); gap: 18px; padding: 16px; }
.sidebar { position: sticky; top: 16px; height: calc(100vh - 32px); display: flex; flex-direction: column; padding: 16px 12px; border: 1px solid rgba(218,227,239,.95); border-radius: 22px; background: rgba(250,252,255,.9); box-shadow: 0 18px 45px rgba(37,58,88,.08); backdrop-filter: blur(14px); }
.brand { display: flex; align-items: center; gap: 12px; padding: 7px 8px 18px; border-bottom: 1px solid #e8edf3; }
.brand-mark { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center; color: #fff; font-weight: 800; font-size: 14px; background: linear-gradient(145deg,#3e77e8,#675ce4); box-shadow: 0 9px 18px rgba(72,103,213,.2); }
.brand strong,.brand span { display:block; }.brand strong{color:#1f2e47;font-size:15px}.brand span{margin-top:3px;color:#929eaf;font-size:11px}
.nav-list { margin-top: 16px; display: grid; gap: 7px; }
.nav-item { width:100%; border:0; background:transparent; padding:11px 12px; border-radius:14px; display:flex; gap:11px; align-items:center; text-align:left; color:#6f7e94; cursor:pointer; transition:.18s ease; }
.nav-item:hover { background:#f0f5fb; color:#315fc8; transform:translateX(1px); }.nav-item.active { background:linear-gradient(100deg,#e9f1ff,#eff4fc); color:#315fc8; box-shadow:inset 0 0 0 1px #dce7fa; }
.nav-item .el-icon { font-size:18px; flex:0 0 auto; }.nav-item strong,.nav-item span{display:block}.nav-item strong{font-size:13px;font-weight:650}.nav-item span{margin-top:2px;color:#98a4b4;font-size:10px}.nav-item.active span{color:#7f93bc}
.sidebar-spacer { flex:1; }.runtime-card{padding:13px;border:1px solid #e0e7f0;border-radius:15px;background:#f7f9fc}.runtime-title{display:flex;align-items:center;gap:7px;color:#8491a4;font-size:10px;letter-spacing:.05em}.status-dot{width:8px;height:8px;border-radius:50%;background:#31b985;box-shadow:0 0 0 4px rgba(49,185,133,.1)}.runtime-card strong,.runtime-card>span{display:block}.runtime-card strong{margin-top:8px;color:#2b3b54;font-size:13px}.runtime-card>span{margin-top:3px;color:#8d99a9;font-size:10px;word-break:break-word}.sidebar-setting{margin-top:8px;border:0;background:transparent;padding:10px 12px;border-radius:12px;display:flex;align-items:center;gap:8px;color:#78869a;cursor:pointer;font-size:12px}.sidebar-setting:hover{background:#f0f4f9;color:#315fc8}
.main-panel { min-width:0; padding: 4px 4px 28px; }.topbar{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;padding:4px 2px 14px}.eyebrow{color:#5c79c6;font-size:10px;font-weight:800;letter-spacing:.15em}.title-group h1{margin:6px 0 5px;color:#16253f;font-size:30px;line-height:1.15;letter-spacing:-.04em}.title-group p{margin:0;color:#7f8c9f;font-size:13px}.toolbar{display:flex;align-items:flex-end;gap:9px;flex-wrap:wrap;justify-content:flex-end}.product-picker>span{display:block;margin-bottom:5px;color:#8491a3;font-size:11px}.product-select{width:220px}.context-strip{margin-bottom:12px;display:flex;align-items:center;gap:9px;padding:10px 13px;border:1px solid #dfe7f1;border-radius:14px;background:rgba(249,251,254,.75);color:#8793a5;font-size:12px}.context-strip span{color:#4169ca;font-weight:700}.context-strip b{color:#36475f}.context-strip em{margin-left:auto;font-style:normal}.message-alert{margin-bottom:12px}.page-host{min-width:0}.loading-page{min-height:500px;display:grid;place-items:center;color:#8b98aa}
.el-button { min-height: 36px; border-radius: 11px !important; font-size: 12px !important; }.el-button--primary{border-color:#3e6fd5 !important;background:#3e6fd5 !important;box-shadow:0 7px 16px rgba(62,111,213,.17)}.el-input__wrapper,.el-select__wrapper{min-height:36px!important;border-radius:11px!important;background:#fff!important;box-shadow:0 0 0 1px #dfe6ef inset!important}.el-select__selected-item,.el-input__inner{font-size:12px!important}.el-alert{border-radius:13px!important}.el-alert__title{font-size:12px!important}.el-table{--el-table-border-color:#e9eef4;--el-table-header-bg-color:#f6f8fb;--el-table-tr-bg-color:transparent;--el-table-row-hover-bg-color:#f5f8fc;--el-table-text-color:#59687d;--el-table-header-text-color:#7f8da1;font-size:12px!important}.el-table th.el-table__cell,.el-table td.el-table__cell{padding:11px 0!important}.el-table .cell{padding:0 8px!important}.el-collapse{border-top:0!important;border-bottom:0!important}.el-collapse-item__header{height:auto!important;min-height:64px;border-bottom:1px solid #e9eef4!important;background:transparent!important}.el-collapse-item__wrap{background:transparent!important;border-bottom:1px solid #e9eef4!important}.el-radio-button__inner{font-size:12px!important}.el-date-editor{min-width:300px}
@media(max-width:980px){.app-shell{grid-template-columns:1fr;padding:10px}.sidebar{position:static;height:auto;flex-direction:row;align-items:center;overflow-x:auto;border-radius:18px}.brand{border-bottom:0;border-right:1px solid #e6ebf2;padding:4px 12px 4px 2px;flex:0 0 auto}.brand span,.runtime-card,.sidebar-setting,.sidebar-spacer{display:none}.nav-list{margin:0;display:flex;gap:6px}.nav-item{flex:0 0 auto;width:auto}.nav-item span{display:none}.main-panel{padding:2px}.topbar{flex-direction:column}.toolbar{justify-content:flex-start;width:100%}.context-strip em{display:none}}
@media(max-width:620px){.title-group h1{font-size:25px}.toolbar{align-items:stretch}.product-picker,.product-select{width:100%}.context-strip{flex-wrap:wrap}.brand div:last-child{display:none}}
</style>
