<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  Box,
  CircleCheck,
  CircleClose,
  DataAnalysis,
  HomeFilled,
  Link,
  Lightning,
  Monitor,
  Money,
  Refresh,
  Search,
  Setting,
  TrendCharts,
} from '@element-plus/icons-vue'
import { api } from './api/client'

type Product = {
  id: number
  name: string
  sku?: string | null
  search_keyword?: string | null
  cost: number
  current_price: number
  min_margin_rate: number
  stock: number
}

type Competitor = {
  id: number
  name: string
  source_type: string
  mock_index: number
  active: boolean
}

type TaobaoItem = {
  rank: number
  competitor_id: number
  title: string
  price: number
  sales: number
  sales_text: string
  shop_name?: string | null
  url?: string | null
  image_url?: string | null
  collected_at: string
}

type TaobaoPayload = {
  product_id: number
  keyword: string
  source: string
  queried_at: string | null
  count: number
  notice?: string | null
  items: TaobaoItem[]
}

const products = ref<Product[]>([])
const selectedId = ref<number | null>(null)
const competitors = ref<Competitor[]>([])
const history = ref<any[]>([])
const recs = ref<any[]>([])
const runs = ref<any[]>([])
const taobaoData = ref<TaobaoPayload | null>(null)
const busy = ref(false)
const taobaoLoading = ref(false)
const message = ref('')
type AlertType = 'success' | 'info' | 'warning' | 'error'
const messageType = ref<AlertType>('info')

let priceChart: echarts.ECharts | null = null

const selected = computed(
  () => products.value.find((item) => item.id === selectedId.value) || null,
)

const grossMarginRate = computed(() => {
  if (!selected.value || !selected.value.current_price) return 0
  return Math.round(
    ((selected.value.current_price - selected.value.cost) /
      selected.value.current_price) *
      100,
  )
})

const minSafePrice = computed(() => {
  if (!selected.value) return 0
  const floor = selected.value.cost / (1 - selected.value.min_margin_rate)
  return Math.round(floor * 100) / 100
})

const latestRun = computed(() => runs.value[0] || null)
const latestRecommendation = computed(() => recs.value[0] || null)
const taobaoItems = computed(() => taobaoData.value?.items || [])
const activeCompetitorCount = computed(
  () => competitors.value.filter((item) => item.active !== false).length,
)

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

function formatTime(value?: string | null) {
  if (!value) return '尚未查询'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

async function loadProducts() {
  try {
    products.value = (await api.get('/products')).data
    if (!selectedId.value && products.value.length) {
      selectedId.value = products.value[0].id
    }
    if (selectedId.value) await loadDetail()
  } catch (error) {
    setMessage(`商品数据加载失败：${humanError(error)}`, 'error')
  }
}

async function loadDetail() {
  if (!selectedId.value) return
  const id = selectedId.value
  try {
    const [c, h, r, u, t] = await Promise.all([
      api.get(`/products/${id}/competitors`),
      api.get(`/products/${id}/price-history`),
      api.get(`/products/${id}/recommendations`),
      api.get(`/products/${id}/runs`),
      api.get(`/products/${id}/competitors/taobao/latest`),
    ])

    competitors.value = c.data
    history.value = h.data
    recs.value = r.data
    runs.value = u.data
    taobaoData.value = t.data

    await nextTick()
    drawChart()
  } catch (error) {
    setMessage(`当前商品数据加载失败：${humanError(error)}`, 'error')
  }
}

async function seed() {
  busy.value = true
  try {
    const response = await api.post('/demo/seed')
    selectedId.value = response.data.product_id
    await loadProducts()
    setMessage('三个演示商品及基础数据已完成幂等初始化。', 'success')
  } catch (error) {
    setMessage(humanError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function advance() {
  if (!selectedId.value) return
  busy.value = true
  try {
    await api.post(`/demo/products/${selectedId.value}/advance`)
    setMessage('当前商品的 Mock 竞品场景已推进。', 'success')
    await loadDetail()
  } catch (error) {
    setMessage(humanError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function searchTaobao() {
  if (!selectedId.value || taobaoLoading.value) return
  taobaoLoading.value = true
  try {
    const response = await api.post(
      `/products/${selectedId.value}/competitors/search-taobao`,
      null,
      { timeout: 65000 },
    )
    taobaoData.value = response.data
    const suffix = response.data.notice ? ` ${response.data.notice}` : ''
    setMessage(`淘宝竞品查询完成，共展示 ${response.data.count} 条。${suffix}`, 'success')
    await loadDetail()
  } catch (error) {
    // 查询失败不清空已有淘宝结果，避免整个 Dashboard 因一次采集失败失去可用状态。
    setMessage(humanError(error), 'error')
  } finally {
    taobaoLoading.value = false
  }
}

async function analyze() {
  if (!selectedId.value) return
  busy.value = true
  try {
    await api.post(`/products/${selectedId.value}/analyze`, null, { timeout: 70000 })
    setMessage('Agent 定价分析完成。', 'success')
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
    setMessage(
      response.data.ok
        ? `LLM 连接正常：${response.data.model}`
        : `LLM 连接失败：${response.data.error}`,
      response.data.ok ? 'success' : 'warning',
    )
  } catch (error) {
    setMessage(humanError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function accept(id: number) {
  await api.post(`/recommendations/${id}/accept`)
  await loadDetail()
}

async function reject(id: number) {
  await api.post(`/recommendations/${id}/reject`)
  await loadDetail()
}

function drawChart() {
  const el = document.getElementById('priceChart')
  if (!el) return
  if (!priceChart) priceChart = echarts.init(el)

  const visibleSeries = history.value.filter((item: any) => item.points?.length)
  const times = Array.from(
    new Set(
      visibleSeries.flatMap((item: any) =>
        item.points.map((point: any) => point.time.replace('T', ' ').slice(5, 16)),
      ),
    ),
  )

  priceChart.setOption(
    {
      animationDuration: 350,
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#ffffff',
        borderColor: '#dce5f3',
        textStyle: { color: '#23304a' },
      },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 14,
        itemHeight: 7,
        textStyle: { color: '#66738b', fontSize: 10 },
      },
      grid: { left: 42, right: 12, top: 40, bottom: 26 },
      xAxis: {
        type: 'category',
        data: times,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#dbe4f0' } },
        axisTick: { show: false },
        axisLabel: { color: '#8190a8', fontSize: 9 },
      },
      yAxis: {
        type: 'value',
        name: '价格 / ¥',
        nameTextStyle: { color: '#8190a8', fontSize: 9 },
        splitLine: { lineStyle: { color: '#edf1f7' } },
        axisLabel: { color: '#8190a8', fontSize: 9 },
      },
      series: visibleSeries.map((item: any, index: number) => ({
        name: item.source_type === 'taobao' ? `淘宝·${item.name}` : item.name,
        type: 'line',
        smooth: 0.3,
        symbol: 'circle',
        symbolSize: 4,
        showSymbol: item.points.length <= 2,
        lineStyle: { width: item.source_type === 'taobao' ? 2.2 : 1.6 },
        areaStyle: index === 0 ? { opacity: 0.04 } : undefined,
        data: item.points.map((point: any) => point.price),
      })),
    },
    true,
  )
}

function handleResize() {
  priceChart?.resize()
}

onMounted(() => {
  loadProducts()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  priceChart?.dispose()
  priceChart = null
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">OP</div>
        <div>
          <strong>OPC Agent</strong>
          <span>Pricing Console</span>
        </div>
      </div>

      <nav class="nav-list">
        <a class="nav-item active" href="#overview"><el-icon><HomeFilled /></el-icon><span>总览</span></a>
        <a class="nav-item" href="#monitoring"><el-icon><Monitor /></el-icon><span>竞品监控</span></a>
        <a class="nav-item" href="#recommendation"><el-icon><DataAnalysis /></el-icon><span>定价建议</span></a>
        <a class="nav-item" href="#audit"><el-icon><TrendCharts /></el-icon><span>运行审计</span></a>
      </nav>

      <div class="sidebar-spacer" />

      <div class="runtime-card">
        <div class="runtime-title"><span class="status-dot" />Agent Runtime</div>
        <strong>{{ latestRun ? latestRun.status : '等待运行' }}</strong>
        <span>{{ latestRun ? `${latestRun.provider} / ${latestRun.model}` : '暂无执行记录' }}</span>
      </div>

      <button class="sidebar-setting" type="button" @click="testLLM">
        <el-icon><Setting /></el-icon><span>连接测试</span>
      </button>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="title-group">
          <span class="eyebrow">SMART PRICING WORKSPACE</span>
          <h1>竞品监测与智能定价</h1>
          <p>淘宝手动查询与 Agent 分析相互独立，数据先入库，再由后端工具读取。</p>
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

      <div class="demo-note">
        商品成本按项目配置；当前售价、库存、销量与 Mock 竞品属于演示基础数据。淘宝卡片只展示手动查询后真实抓取并入库的数据。
      </div>

      <el-alert
        v-if="message"
        class="message-alert"
        :title="message"
        :type="messageType"
        show-icon
        :closable="true"
        @close="message = ''"
      />

      <template v-if="selected">
        <section id="overview" class="summary-grid">
          <article class="metric-card">
            <div class="metric-icon"><el-icon><Money /></el-icon></div>
            <div class="metric-copy"><span>当前售价</span><strong>¥{{ selected.current_price }}</strong><small>演示基础售价</small></div>
          </article>
          <article class="metric-card">
            <div class="metric-icon"><el-icon><TrendCharts /></el-icon></div>
            <div class="metric-copy"><span>最低安全价</span><strong>¥{{ minSafePrice }}</strong><small>成本 ¥{{ selected.cost }} · 毛利 {{ grossMarginRate }}%</small></div>
          </article>
          <article class="metric-card">
            <div class="metric-icon"><el-icon><Box /></el-icon></div>
            <div class="metric-copy"><span>可用库存</span><strong>{{ selected.stock }}</strong><small>演示库存数据</small></div>
          </article>
          <article class="metric-card">
            <div class="metric-icon"><el-icon><Monitor /></el-icon></div>
            <div class="metric-copy"><span>当前竞品</span><strong>{{ taobaoItems.length || activeCompetitorCount }}</strong><small>{{ taobaoItems.length ? '淘宝最近一次 Top5' : '当前启用监控项' }}</small></div>
          </article>
        </section>

        <section class="dashboard-grid">
          <article class="panel chart-panel">
            <div class="panel-head">
              <div><span class="panel-kicker">MARKET TREND</span><h2>价格趋势</h2></div>
              <span class="soft-badge">按当前商品切换</span>
            </div>
            <div id="priceChart" class="price-chart" />
          </article>

          <article id="monitoring" class="panel monitor-panel">
            <div class="panel-head monitor-head">
              <div>
                <span class="panel-kicker">TAOBAO COMPETITORS</span>
                <h2>竞品监控</h2>
              </div>
              <el-button type="primary" :icon="Search" :loading="taobaoLoading" :disabled="taobaoLoading" @click="searchTaobao">
                {{ taobaoLoading ? '正在查询...' : '查询淘宝竞品' }}
              </el-button>
            </div>

            <div class="source-line">
              <div><span class="source-dot" />淘宝数据</div>
              <span>最近查询：{{ formatTime(taobaoData?.queried_at) }}</span>
            </div>
            <div v-if="taobaoData?.keyword" class="keyword-line">搜索词：{{ taobaoData.keyword }}</div>

            <el-table v-if="taobaoItems.length" class="compact-table" :data="taobaoItems" height="238">
              <el-table-column prop="rank" label="#" width="38" align="center" />
              <el-table-column label="商品" min-width="150">
                <template #default="scope">
                  <div class="product-cell">
                    <img v-if="scope.row.image_url" :src="scope.row.image_url" alt="" />
                    <span :title="scope.row.title">{{ scope.row.title }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="价格" width="72"><template #default="scope">¥{{ scope.row.price }}</template></el-table-column>
              <el-table-column label="销量" width="78"><template #default="scope">{{ scope.row.sales_text }}</template></el-table-column>
              <el-table-column prop="shop_name" label="店铺" min-width="90" show-overflow-tooltip />
              <el-table-column label="操作" width="58" align="center">
                <template #default="scope">
                  <a v-if="scope.row.url" class="view-link" :href="scope.row.url" target="_blank" rel="noopener noreferrer"><el-icon><Link /></el-icon>查看</a>
                </template>
              </el-table-column>
            </el-table>
            <div v-else class="taobao-empty">
              <el-icon><Search /></el-icon>
              <strong>尚无淘宝查询数据</strong>
              <span>先在本机完成淘宝登录，再点击右上角按钮。</span>
            </div>

            <div class="monitor-foot">
              <span>Top5 仅指本次搜索结果中有销量数据的商品。</span>
              <el-button text :loading="busy" @click="advance">推进 Mock 场景</el-button>
            </div>
          </article>

          <article id="recommendation" class="panel recommendation-panel">
            <div class="panel-head">
              <div><span class="panel-kicker">AGENT DECISION</span><h2>Agent 定价建议</h2></div>
              <span v-if="latestRecommendation" class="decision-status" :class="`is-${latestRecommendation.status}`">{{ latestRecommendation.status }}</span>
            </div>

            <div v-if="latestRecommendation" class="recommendation-content">
              <div class="decision-row">
                <el-tag effect="dark" round>{{ latestRecommendation.action }}</el-tag>
                <div class="price-suggestion" v-if="latestRecommendation.suggested_price"><span>建议价格</span><strong>¥{{ latestRecommendation.suggested_price }}</strong></div>
                <div class="completeness"><span>数据完整度</span><strong>{{ latestRecommendation.data_completeness }}</strong></div>
              </div>
              <div class="rec-section"><h3>主要证据</h3><ul><li v-for="item in latestRecommendation.evidence_summary" :key="item">{{ item }}</li></ul></div>
              <div class="rec-section risk-section"><h3>风险提示</h3><ul><li v-for="item in latestRecommendation.risk_notes" :key="item">{{ item }}</li></ul></div>
              <div class="decision-actions">
                <el-button type="success" :icon="CircleCheck" @click="accept(latestRecommendation.id)">接受建议</el-button>
                <el-button plain type="danger" :icon="CircleClose" @click="reject(latestRecommendation.id)">拒绝建议</el-button>
              </div>
            </div>
            <div v-else class="rec-empty">
              <DataAnalysis class="empty-svg" />
              <strong>尚无定价建议</strong>
              <span>淘宝查询完成后，可单独点击顶部“Agent 定价分析”。</span>
            </div>
          </article>

          <article id="audit" class="panel audit-panel">
            <div class="panel-head">
              <div><span class="panel-kicker">EXECUTION TRACE</span><h2>Agent 执行 / 审计记录</h2></div>
              <span class="soft-badge">{{ runs.length }} 次运行</span>
            </div>
            <div v-if="runs.length" class="run-list">
              <div v-for="run in runs" :key="run.id" class="run-card">
                <div class="run-head">
                  <div><strong>Run #{{ run.id }}</strong><span>{{ formatTime(run.started_at) }}</span></div>
                  <div class="run-meta"><span>{{ run.provider }} / {{ run.model }}</span><b>{{ run.status }}</b></div>
                </div>
                <div class="tool-strip">
                  <div v-for="(tool, index) in run.tool_calls" :key="index" class="tool-item">
                    <div class="tool-title"><span>{{ index + 1 }}</span><strong>{{ tool.tool_name }}</strong><small>{{ tool.duration_ms }} ms</small></div>
                    <p>{{ tool.result_summary }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="rec-empty small"><strong>暂无 Agent Run</strong><span>运行一次 Agent 后，这里会显示工具调用审计。</span></div>
          </article>
        </section>
      </template>

      <section v-else class="empty-state"><el-empty description="暂无商品数据" /></section>
    </main>
  </div>
</template>

<style scoped>
:global(*) { box-sizing: border-box; }
:global(html) { scroll-behavior: smooth; }
:global(body) {
  margin: 0;
  min-width: 320px;
  background: #f4f7fb;
  color: #202b3f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}
:global(button), :global(input), :global(.el-select) { font-family: inherit; }

.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 196px minmax(0, 1fr);
  max-width: 1560px;
  margin: 0 auto;
  padding: 14px;
  gap: 12px;
}

.sidebar {
  position: sticky;
  top: 14px;
  align-self: start;
  height: calc(100vh - 28px);
  padding: 16px 12px;
  border: 1px solid #e2e9f3;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(34, 57, 94, 0.06);
  display: flex;
  flex-direction: column;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 2px 6px 18px; }
.brand-mark {
  width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center;
  font-weight: 800; font-size: 11px; color: #fff; background: linear-gradient(135deg, #4779ea, #6657df);
  box-shadow: 0 7px 18px rgba(75, 100, 215, 0.2);
}
.brand strong, .brand span { display: block; }
.brand strong { font-size: 13px; }
.brand span { margin-top: 2px; color: #8a97aa; font-size: 9px; }
.nav-list { display: flex; flex-direction: column; gap: 5px; }
.nav-item {
  min-height: 38px; display: flex; align-items: center; gap: 9px; padding: 0 11px; border-radius: 10px;
  color: #6e7b8f; text-decoration: none; font-size: 11px; transition: .18s ease;
}
.nav-item:hover, .nav-item.active { color: #315fcb; background: #eef4ff; }
.nav-item .el-icon { font-size: 14px; }
.sidebar-spacer { flex: 1; }
.runtime-card { padding: 12px; border: 1px solid #e5ebf4; border-radius: 12px; background: #f8faff; }
.runtime-title { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; color: #8390a4; font-size: 9px; letter-spacing: .06em; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #31ba88; box-shadow: 0 0 0 3px rgba(49,186,136,.11); }
.runtime-card strong, .runtime-card span { display: block; }
.runtime-card strong { font-size: 12px; color: #27344b; }
.runtime-card > span { margin-top: 3px; color: #8a97aa; font-size: 9px; word-break: break-word; }
.sidebar-setting { border: 0; background: transparent; color: #77859a; margin-top: 7px; padding: 9px 11px; border-radius: 10px; display: flex; align-items: center; gap: 7px; cursor: pointer; font-size: 10px; }
.sidebar-setting:hover { background: #f2f6fb; color: #315fcb; }

.main-panel { min-width: 0; padding: 6px 4px 20px; }
.topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 9px; }
.eyebrow, .panel-kicker { color: #5d79bb; font-size: 8px; font-weight: 800; letter-spacing: .13em; }
.title-group h1 { margin: 4px 0; font-size: clamp(21px, 2vw, 28px); line-height: 1.15; letter-spacing: -.035em; }
.title-group p { margin: 0; color: #7c899d; font-size: 11px; }
.toolbar { display: flex; align-items: flex-end; gap: 7px; flex-wrap: wrap; justify-content: flex-end; }
.product-picker > span { display: block; margin-bottom: 4px; color: #8591a4; font-size: 9px; }
.product-select { width: 190px; }
.demo-note { margin-bottom: 9px; padding: 8px 11px; border: 1px solid #e0e8f4; border-radius: 10px; background: #f9fbfe; color: #75849a; font-size: 9px; line-height: 1.5; }
.message-alert { margin-bottom: 9px; }

.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9px; margin-bottom: 9px; }
.metric-card, .panel { border: 1px solid #e1e8f1; background: #ffffff; box-shadow: 0 5px 16px rgba(36, 58, 91, 0.045); }
.metric-card { min-height: 84px; border-radius: 13px; padding: 11px 12px; display: flex; align-items: center; gap: 10px; }
.metric-icon { width: 32px; height: 32px; flex: 0 0 auto; border-radius: 10px; display: grid; place-items: center; color: #476ed0; background: #eef4ff; border: 1px solid #e0e9fb; }
.metric-copy span, .metric-copy strong, .metric-copy small { display: block; }
.metric-copy > span { color: #7b899e; font-size: 9px; }
.metric-copy strong { margin: 2px 0; color: #24334b; font-size: 19px; line-height: 1.1; letter-spacing: -.035em; }
.metric-copy small { color: #98a3b3; font-size: 8px; }

.dashboard-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 9px; }
.panel { min-width: 0; border-radius: 13px; padding: 13px; }
.chart-panel { grid-column: span 7; }
.monitor-panel { grid-column: span 5; }
.recommendation-panel { grid-column: span 5; }
.audit-panel { grid-column: span 7; }
.panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.panel-head h2 { margin: 3px 0 0; font-size: 13px; font-weight: 680; letter-spacing: -.015em; }
.soft-badge, .decision-status { flex: 0 0 auto; border: 1px solid #e2e9f3; background: #f7f9fc; color: #77869a; border-radius: 999px; font-size: 8px; padding: 4px 7px; }
.decision-status.is-accepted { color: #1b8c66; border-color: #cfeadf; background: #effaf6; }
.decision-status.is-rejected { color: #c6545f; border-color: #f1d5d9; background: #fff5f6; }
.price-chart { height: 232px; }

.monitor-head { align-items: center; }
.source-line { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 4px; color: #8995a7; font-size: 8px; }
.source-line > div { display: flex; align-items: center; gap: 5px; color: #52627a; font-weight: 650; }
.source-dot { width: 6px; height: 6px; border-radius: 50%; background: #ff7a45; }
.keyword-line { margin-bottom: 7px; color: #97a3b3; font-size: 8px; }
.product-cell { display: flex; align-items: center; gap: 6px; min-width: 0; }
.product-cell img { width: 28px; height: 28px; border-radius: 6px; object-fit: cover; flex: 0 0 auto; border: 1px solid #e8edf4; }
.product-cell span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.view-link { display: inline-flex; align-items: center; gap: 2px; color: #3569d4; text-decoration: none; font-size: 9px; }
.taobao-empty { height: 202px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9aa5b4; text-align: center; }
.taobao-empty .el-icon { font-size: 26px; color: #b6c3d6; margin-bottom: 7px; }
.taobao-empty strong { color: #69778c; font-size: 10px; }
.taobao-empty span { margin-top: 4px; font-size: 8px; }
.monitor-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 7px; color: #98a4b4; font-size: 8px; }

.recommendation-content { display: flex; flex-direction: column; gap: 10px; }
.decision-row { display: grid; grid-template-columns: auto 1fr 1fr; align-items: center; gap: 8px; padding: 9px; border-radius: 10px; background: #f7f9fd; border: 1px solid #e8edf5; }
.price-suggestion span, .price-suggestion strong, .completeness span, .completeness strong { display: block; }
.price-suggestion span, .completeness span { color: #8d99aa; font-size: 8px; }
.price-suggestion strong, .completeness strong { margin-top: 2px; color: #2c3950; font-size: 14px; }
.rec-section h3 { margin: 0 0 5px; color: #59677c; font-size: 9px; font-weight: 650; }
.rec-section ul { margin: 0; padding-left: 15px; color: #728096; font-size: 9px; line-height: 1.6; }
.risk-section { padding-top: 7px; border-top: 1px solid #edf1f6; }
.decision-actions { display: flex; gap: 7px; }
.rec-empty { min-height: 224px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: #9aa5b4; }
.rec-empty.small { min-height: 180px; }
.empty-svg { width: 30px; margin-bottom: 7px; color: #b7c3d5; }
.rec-empty strong { color: #67768b; font-size: 10px; }
.rec-empty span { margin-top: 4px; font-size: 8px; }

.run-list { max-height: 300px; overflow: auto; padding-right: 2px; }
.run-card { padding: 10px; border: 1px solid #e8edf4; border-radius: 10px; background: #fafbfd; }
.run-card + .run-card { margin-top: 7px; }
.run-head { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
.run-head strong, .run-head span { display: block; }
.run-head strong { font-size: 10px; color: #334158; }
.run-head span { margin-top: 2px; color: #929eaf; font-size: 8px; }
.run-meta { text-align: right; }
.run-meta b { display: inline-block; margin-top: 3px; color: #278566; font-size: 8px; font-weight: 650; }
.tool-strip { margin-top: 7px; display: grid; gap: 5px; }
.tool-item { padding: 7px 8px; border-radius: 8px; background: #f2f6fb; }
.tool-title { display: flex; align-items: center; gap: 6px; }
.tool-title > span { width: 16px; height: 16px; border-radius: 5px; display: grid; place-items: center; background: #e5edfa; color: #5473ac; font-size: 7px; }
.tool-title strong { font-size: 9px; color: #46546a; }
.tool-title small { margin-left: auto; color: #9aa5b4; font-size: 7px; }
.tool-item p { margin: 5px 0 0 22px; color: #78869a; font-size: 8px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
.empty-state { min-height: 420px; display: grid; place-items: center; }

:deep(.el-button) { height: 32px; border-radius: 9px; font-size: 10px; }
:deep(.el-button--primary) { border-color: #416fda; background: #416fda; box-shadow: 0 5px 12px rgba(65,111,218,.13); }
:deep(.el-button--success) { border-color: #bfe6d7; background: #effaf6; color: #21805f; }
:deep(.el-button--danger) { border-color: #efd2d6; background: #fff6f7; color: #be5661; }
:deep(.el-input__wrapper), :deep(.el-select__wrapper) { min-height: 32px; border-radius: 9px; background: #fff; box-shadow: 0 0 0 1px #dfe6ef inset !important; }
:deep(.el-input__inner), :deep(.el-select__placeholder), :deep(.el-select__selected-item) { color: #3a485d; font-size: 10px; }
:deep(.el-alert) { border-radius: 9px; }
:deep(.el-alert__title) { font-size: 9px; }
:deep(.el-table) {
  --el-table-border-color: #edf1f5;
  --el-table-header-bg-color: #f7f9fc;
  --el-table-tr-bg-color: #ffffff;
  --el-table-row-hover-bg-color: #f7faff;
  --el-table-text-color: #59677a;
  --el-table-header-text-color: #8490a2;
  font-size: 9px;
}
:deep(.el-table th.el-table__cell), :deep(.el-table td.el-table__cell) { padding: 6px 0; }
:deep(.el-table .cell) { padding: 0 5px; }
:deep(.el-tag) { border: 0; background: #4b73d2; font-size: 8px; }

@media (max-width: 1120px) {
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .chart-panel, .monitor-panel, .recommendation-panel, .audit-panel { grid-column: span 6; }
}
@media (max-width: 860px) {
  .app-shell { display: block; padding: 9px; }
  .sidebar { position: static; height: auto; margin-bottom: 9px; padding: 9px; flex-direction: row; align-items: center; gap: 7px; overflow-x: auto; border-radius: 14px; }
  .brand { padding: 0 7px 0 0; flex: 0 0 auto; }
  .brand span, .runtime-card, .sidebar-setting, .sidebar-spacer { display: none; }
  .nav-list { flex-direction: row; }
  .nav-item { flex: 0 0 auto; min-height: 34px; }
  .main-panel { padding: 4px; }
  .topbar { flex-direction: column; }
  .toolbar { width: 100%; justify-content: flex-start; }
  .chart-panel, .monitor-panel, .recommendation-panel, .audit-panel { grid-column: 1 / -1; }
}
@media (max-width: 560px) {
  .summary-grid { grid-template-columns: 1fr 1fr; }
  .metric-card { min-height: 76px; padding: 9px; }
  .metric-icon { display: none; }
  .metric-copy strong { font-size: 17px; }
  .toolbar .el-button { flex: 1; }
  .product-picker, .product-select { width: 100%; }
  .decision-row { grid-template-columns: 1fr 1fr; }
  .decision-row .el-tag { grid-column: 1 / -1; justify-self: start; }
  .decision-actions { flex-direction: column; }
  .run-head { flex-direction: column; }
  .run-meta { text-align: left; }
}
</style>
