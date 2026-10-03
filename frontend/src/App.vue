<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  Box,
  CircleCheck,
  CircleClose,
  DataAnalysis,
  Goods,
  HomeFilled,
  Lightning,
  Monitor,
  Money,
  Refresh,
  Setting,
  TrendCharts,
} from '@element-plus/icons-vue'
import { api } from './api/client'

type Product = {
  id: number
  name: string
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
}

const products = ref<Product[]>([])
const selectedId = ref<number | null>(null)
const competitors = ref<Competitor[]>([])
const history = ref<any[]>([])
const recs = ref<any[]>([])
const runs = ref<any[]>([])
const busy = ref(false)
const message = ref('')

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

const latestRun = computed(() => runs.value[0] || null)
const latestRecommendation = computed(() => recs.value[0] || null)

async function loadProducts() {
  products.value = (await api.get('/products')).data

  if (!selectedId.value && products.value.length) {
    selectedId.value = products.value[0].id
  }

  if (selectedId.value) await loadDetail()
}

async function loadDetail() {
  if (!selectedId.value) return
  const id = selectedId.value

  const [c, h, r, u] = await Promise.all([
    api.get(`/products/${id}/competitors`),
    api.get(`/products/${id}/price-history`),
    api.get(`/products/${id}/recommendations`),
    api.get(`/products/${id}/runs`),
  ])

  competitors.value = c.data
  history.value = h.data
  recs.value = r.data
  runs.value = u.data

  await nextTick()
  drawChart()
}

async function seed() {
  busy.value = true
  try {
    const response = await api.post('/demo/seed')
    selectedId.value = response.data.product_id
    await loadProducts()
    message.value = 'Demo 数据已初始化'
  } finally {
    busy.value = false
  }
}

async function advance() {
  if (!selectedId.value) return
  busy.value = true
  try {
    const response = await api.post(`/demo/products/${selectedId.value}/advance`)
    message.value = `Mock 场景已推进：${JSON.stringify(response.data.results)}`
    await loadDetail()
  } finally {
    busy.value = false
  }
}

async function analyze() {
  if (!selectedId.value) return
  busy.value = true
  try {
    await api.post(`/products/${selectedId.value}/analyze`)
    message.value = 'Agent 分析完成'
    await loadDetail()
  } finally {
    busy.value = false
  }
}

async function testLLM() {
  busy.value = true
  try {
    const response = await api.post('/settings/llm/test')
    message.value = JSON.stringify(response.data)
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

  const times = Array.from(
    new Set(
      history.value.flatMap((item: any) =>
        item.points.map((point: any) => point.time.slice(11, 19)),
      ),
    ),
  )

  priceChart.setOption(
    {
      animationDuration: 500,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(16, 31, 66, .96)',
        borderColor: 'rgba(148, 181, 255, .22)',
        textStyle: { color: '#f7fbff' },
      },
      legend: {
        top: 2,
        right: 0,
        itemWidth: 16,
        itemHeight: 8,
        textStyle: { color: '#aab9db', fontSize: 11 },
      },
      grid: { left: 38, right: 16, top: 44, bottom: 28 },
      xAxis: {
        type: 'category',
        data: times,
        boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(151, 173, 221, .18)' } },
        axisTick: { show: false },
        axisLabel: { color: '#7183aa', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        name: '价格 / ¥',
        nameTextStyle: { color: '#7183aa', fontSize: 10, padding: [0, 0, 6, 0] },
        splitLine: { lineStyle: { color: 'rgba(151, 173, 221, .10)' } },
        axisLabel: { color: '#7183aa', fontSize: 10 },
      },
      series: history.value.map((item: any, index: number) => ({
        name: item.name,
        type: 'line',
        smooth: 0.35,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        lineStyle: { width: 2 },
        emphasis: { focus: 'series' },
        areaStyle:
          index === 0
            ? {
                opacity: 0.08,
              }
            : undefined,
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
        <a class="nav-item active" href="#overview">
          <el-icon><HomeFilled /></el-icon>
          <span>总览</span>
        </a>
        <a class="nav-item" href="#monitoring">
          <el-icon><Monitor /></el-icon>
          <span>竞品监控</span>
        </a>
        <a class="nav-item" href="#recommendation">
          <el-icon><DataAnalysis /></el-icon>
          <span>定价建议</span>
        </a>
        <a class="nav-item" href="#audit">
          <el-icon><TrendCharts /></el-icon>
          <span>运行审计</span>
        </a>
      </nav>

      <div class="sidebar-spacer" />

      <div class="runtime-card">
        <div class="runtime-title">
          <span class="status-dot" />
          Agent Runtime
        </div>
        <strong>{{ latestRun ? latestRun.status : '等待运行' }}</strong>
        <span>{{ latestRun ? `${latestRun.provider} / ${latestRun.model}` : '暂无执行记录' }}</span>
      </div>

      <button class="sidebar-setting" type="button" @click="testLLM">
        <el-icon><Setting /></el-icon>
        <span>连接测试</span>
      </button>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <div class="title-group">
          <span class="eyebrow">SMART PRICING WORKSPACE</span>
          <h1>竞品监测与智能定价</h1>
          <p>集中查看价格变化、Agent 分析结果与人工决策状态。</p>
        </div>

        <div class="toolbar">
          <el-select
            v-model="selectedId"
            class="product-select"
            placeholder="选择商品"
            @change="loadDetail"
          >
            <el-option
              v-for="product in products"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>
          <el-button :icon="Refresh" :loading="busy" @click="seed">初始化 Demo</el-button>
          <el-button type="primary" :icon="Lightning" :loading="busy" @click="analyze">
            立即分析
          </el-button>
        </div>
      </header>

      <el-alert
        v-if="message"
        class="message-alert"
        :title="message"
        type="info"
        show-icon
        :closable="true"
        @close="message = ''"
      />

      <template v-if="selected">
        <section id="overview" class="summary-grid">
          <article class="metric-card">
            <div class="metric-icon"><el-icon><Money /></el-icon></div>
            <div class="metric-copy">
              <span>当前售价</span>
              <strong>¥{{ selected.current_price }}</strong>
              <small>核心定价基准</small>
            </div>
          </article>

          <article class="metric-card">
            <div class="metric-icon"><el-icon><Goods /></el-icon></div>
            <div class="metric-copy">
              <span>商品成本</span>
              <strong>¥{{ selected.cost }}</strong>
              <small>成本约束</small>
            </div>
          </article>

          <article class="metric-card">
            <div class="metric-icon"><el-icon><TrendCharts /></el-icon></div>
            <div class="metric-copy">
              <span>当前毛利率</span>
              <strong>{{ grossMarginRate }}%</strong>
              <small>最低要求 {{ Math.round(selected.min_margin_rate * 100) }}%</small>
            </div>
          </article>

          <article class="metric-card">
            <div class="metric-icon"><el-icon><Box /></el-icon></div>
            <div class="metric-copy">
              <span>可用库存</span>
              <strong>{{ selected.stock }}</strong>
              <small>{{ competitors.length }} 个竞品正在监控</small>
            </div>
          </article>
        </section>

        <section class="dashboard-grid">
          <article class="panel chart-panel">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">MARKET TREND</span>
                <h2>竞品价格历史</h2>
              </div>
              <span class="soft-badge">实时对比</span>
            </div>
            <div id="priceChart" class="price-chart" />
          </article>

          <article id="monitoring" class="panel monitor-panel">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">COMPETITORS</span>
                <h2>竞品监控</h2>
              </div>
              <span class="count-badge">{{ competitors.length }}</span>
            </div>

            <el-table class="compact-table" :data="competitors" height="246">
              <el-table-column prop="name" label="竞品" min-width="115" />
              <el-table-column prop="source_type" label="来源" width="82" />
              <el-table-column prop="mock_index" label="阶段" width="68" align="right" />
            </el-table>

            <el-button class="scenario-button" plain :loading="busy" @click="advance">
              推进 Mock 场景
            </el-button>
          </article>

          <article id="recommendation" class="panel recommendation-panel">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">AGENT DECISION</span>
                <h2>最新定价建议</h2>
              </div>
              <span
                v-if="latestRecommendation"
                class="decision-status"
                :class="`is-${latestRecommendation.status}`"
              >
                {{ latestRecommendation.status }}
              </span>
            </div>

            <div v-if="latestRecommendation" class="recommendation-content">
              <div class="decision-row">
                <el-tag effect="dark" round>{{ latestRecommendation.action }}</el-tag>
                <div class="price-suggestion" v-if="latestRecommendation.suggested_price">
                  <span>建议价格</span>
                  <strong>¥{{ latestRecommendation.suggested_price }}</strong>
                </div>
                <div class="completeness">
                  <span>数据完整度</span>
                  <strong>{{ latestRecommendation.data_completeness }}</strong>
                </div>
              </div>

              <div class="rec-section">
                <h3>主要证据</h3>
                <ul>
                  <li v-for="item in latestRecommendation.evidence_summary" :key="item">
                    {{ item }}
                  </li>
                </ul>
              </div>

              <div class="rec-section risk-section">
                <h3>风险提示</h3>
                <ul>
                  <li v-for="item in latestRecommendation.risk_notes" :key="item">
                    {{ item }}
                  </li>
                </ul>
              </div>

              <div class="decision-actions">
                <el-button
                  type="success"
                  :icon="CircleCheck"
                  @click="accept(latestRecommendation.id)"
                >
                  接受建议
                </el-button>
                <el-button
                  plain
                  type="danger"
                  :icon="CircleClose"
                  @click="reject(latestRecommendation.id)"
                >
                  拒绝建议
                </el-button>
              </div>
            </div>

            <el-empty v-else :image-size="72" description="尚无建议，先推进场景并分析" />
          </article>

          <article id="audit" class="panel audit-panel">
            <div class="panel-head">
              <div>
                <span class="panel-kicker">EXECUTION TRACE</span>
                <h2>Agent Run 审计</h2>
              </div>
              <span class="soft-badge">{{ runs.length }} 次运行</span>
            </div>

            <div v-if="runs.length" class="run-list">
              <div v-for="run in runs" :key="run.id" class="run-card">
                <div class="run-head">
                  <div>
                    <strong>Run #{{ run.id }}</strong>
                    <span>{{ run.started_at }}</span>
                  </div>
                  <div class="run-meta">
                    <span>{{ run.provider }} / {{ run.model }}</span>
                    <b>{{ run.status }}</b>
                  </div>
                </div>

                <div class="tool-strip">
                  <div v-for="(tool, index) in run.tool_calls" :key="index" class="tool-item">
                    <div class="tool-title">
                      <span>{{ index + 1 }}</span>
                      <strong>{{ tool.tool_name }}</strong>
                      <small>{{ tool.duration_ms }} ms</small>
                    </div>
                    <p>{{ tool.result_summary }}</p>
                  </div>
                </div>
              </div>
            </div>

            <el-empty v-else :image-size="72" description="暂无 Agent Run" />
          </article>
        </section>
      </template>

      <section v-else class="empty-state">
        <el-empty description="点击右上角初始化 Demo 数据" />
      </section>
    </main>
  </div>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(html) {
  scroll-behavior: smooth;
}

:global(body) {
  margin: 0;
  min-width: 320px;
  background:
    radial-gradient(circle at 18% 12%, rgba(89, 137, 255, 0.24), transparent 30%),
    radial-gradient(circle at 84% 16%, rgba(119, 84, 225, 0.18), transparent 28%),
    linear-gradient(145deg, #07152f 0%, #0b1f43 48%, #09152c 100%);
  color: #eef4ff;
  font-family:
    Inter,
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}

:global(button),
:global(input),
:global(.el-select) {
  font-family: inherit;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 206px minmax(0, 1fr);
  max-width: 1540px;
  margin: 0 auto;
  padding: 16px;
  gap: 14px;
}

.sidebar,
.main-panel {
  border: 1px solid rgba(154, 185, 255, 0.14);
  background: linear-gradient(180deg, rgba(31, 67, 126, 0.5), rgba(12, 32, 69, 0.66));
  box-shadow: 0 22px 60px rgba(2, 8, 23, 0.2);
  backdrop-filter: blur(22px);
}

.sidebar {
  position: sticky;
  top: 16px;
  align-self: start;
  height: calc(100vh - 32px);
  padding: 18px 14px;
  border-radius: 24px;
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 6px 18px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 12px;
  letter-spacing: -0.03em;
  color: white;
  background: linear-gradient(135deg, #75bfff, #6d6aff 70%, #9b73ff);
  box-shadow: 0 10px 24px rgba(96, 122, 255, 0.28);
}

.brand strong,
.brand span {
  display: block;
}

.brand strong {
  font-size: 14px;
  letter-spacing: 0.01em;
}

.brand span {
  margin-top: 2px;
  color: #8195bf;
  font-size: 10px;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 13px;
  color: #9eb0d3;
  text-decoration: none;
  font-size: 12px;
  transition: 0.2s ease;
}

.nav-item .el-icon {
  font-size: 15px;
}

.nav-item:hover,
.nav-item.active {
  color: #f6f9ff;
  border-color: rgba(169, 196, 255, 0.16);
  background: linear-gradient(90deg, rgba(104, 159, 255, 0.24), rgba(109, 91, 219, 0.14));
}

.sidebar-spacer {
  flex: 1;
}

.runtime-card {
  padding: 13px;
  border: 1px solid rgba(150, 185, 255, 0.12);
  border-radius: 15px;
  background: rgba(10, 29, 64, 0.48);
}

.runtime-title {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
  color: #8ea2ca;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #6de0bd;
  box-shadow: 0 0 0 4px rgba(109, 224, 189, 0.09);
}

.runtime-card strong,
.runtime-card span {
  display: block;
}

.runtime-card strong {
  font-size: 13px;
}

.runtime-card > span {
  margin-top: 4px;
  color: #7085af;
  font-size: 10px;
  word-break: break-word;
}

.sidebar-setting {
  border: 0;
  background: transparent;
  color: #879bc3;
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 11px;
}

.sidebar-setting:hover {
  background: rgba(255, 255, 255, 0.04);
  color: white;
}

.main-panel {
  min-width: 0;
  border-radius: 24px;
  padding: 22px;
}

.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.eyebrow,
.panel-kicker {
  color: #6e8fd0;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.title-group h1 {
  margin: 5px 0 5px;
  font-size: clamp(22px, 2.3vw, 30px);
  line-height: 1.15;
  letter-spacing: -0.04em;
}

.title-group p {
  margin: 0;
  color: #8194bd;
  font-size: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.product-select {
  width: 190px;
}

.message-alert {
  margin-bottom: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}

.metric-card,
.panel {
  border: 1px solid rgba(152, 184, 255, 0.12);
  background:
    linear-gradient(180deg, rgba(53, 91, 153, 0.28), rgba(19, 48, 95, 0.36)),
    rgba(12, 33, 73, 0.54);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
}

.metric-card {
  min-height: 102px;
  border-radius: 16px;
  padding: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.metric-icon {
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #bdd7ff;
  background: linear-gradient(145deg, rgba(97, 159, 255, 0.22), rgba(112, 88, 217, 0.14));
  border: 1px solid rgba(156, 193, 255, 0.14);
}

.metric-copy {
  min-width: 0;
}

.metric-copy span,
.metric-copy strong,
.metric-copy small {
  display: block;
}

.metric-copy > span {
  color: #879ac0;
  font-size: 10px;
}

.metric-copy strong {
  margin: 3px 0 2px;
  color: #f7fbff;
  font-size: 21px;
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.metric-copy small {
  color: #6077a5;
  font-size: 9px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 10px;
}

.panel {
  min-width: 0;
  border-radius: 16px;
  padding: 15px;
}

.chart-panel {
  grid-column: span 8;
}

.monitor-panel {
  grid-column: span 4;
}

.recommendation-panel {
  grid-column: span 5;
}

.audit-panel {
  grid-column: span 7;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-head h2 {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.soft-badge,
.count-badge,
.decision-status {
  flex: 0 0 auto;
  border: 1px solid rgba(147, 181, 255, 0.13);
  background: rgba(96, 137, 218, 0.09);
  color: #87a3db;
  border-radius: 999px;
  font-size: 9px;
  padding: 5px 8px;
}

.count-badge {
  min-width: 24px;
  text-align: center;
  color: #b8cbf5;
}

.decision-status.is-accepted {
  color: #89e4c7;
  border-color: rgba(89, 215, 176, 0.16);
  background: rgba(89, 215, 176, 0.08);
}

.decision-status.is-rejected {
  color: #ff9fa9;
  border-color: rgba(255, 126, 141, 0.16);
  background: rgba(255, 126, 141, 0.08);
}

.price-chart {
  height: 256px;
}

.scenario-button {
  width: 100%;
  margin-top: 10px;
}

.recommendation-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.decision-row {
  display: grid;
  grid-template-columns: auto 1fr 1fr;
  align-items: center;
  gap: 9px;
  padding: 11px;
  border-radius: 13px;
  background: linear-gradient(90deg, rgba(92, 125, 225, 0.11), rgba(117, 87, 205, 0.07));
  border: 1px solid rgba(144, 176, 247, 0.09);
}

.price-suggestion span,
.price-suggestion strong,
.completeness span,
.completeness strong {
  display: block;
}

.price-suggestion span,
.completeness span {
  color: #7388b3;
  font-size: 9px;
}

.price-suggestion strong,
.completeness strong {
  margin-top: 2px;
  font-size: 15px;
}

.rec-section {
  padding: 0 2px;
}

.rec-section h3 {
  margin: 0 0 7px;
  color: #b8c8e7;
  font-size: 10px;
  font-weight: 600;
}

.rec-section ul {
  margin: 0;
  padding-left: 16px;
  color: #8296bd;
  font-size: 10px;
  line-height: 1.65;
}

.risk-section {
  padding-top: 9px;
  border-top: 1px solid rgba(151, 180, 237, 0.08);
}

.decision-actions {
  display: flex;
  gap: 8px;
  padding-top: 2px;
}

.run-list {
  max-height: 350px;
  overflow: auto;
  padding-right: 3px;
}

.run-list::-webkit-scrollbar {
  width: 5px;
}

.run-list::-webkit-scrollbar-thumb {
  background: rgba(135, 160, 216, 0.18);
  border-radius: 99px;
}

.run-card {
  padding: 12px;
  border: 1px solid rgba(145, 178, 240, 0.09);
  border-radius: 13px;
  background: rgba(8, 26, 59, 0.3);
}

.run-card + .run-card {
  margin-top: 8px;
}

.run-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.run-head strong,
.run-head span {
  display: block;
}

.run-head strong {
  font-size: 11px;
}

.run-head span {
  margin-top: 3px;
  color: #667da9;
  font-size: 9px;
}

.run-meta {
  text-align: right;
}

.run-meta b {
  display: inline-block;
  margin-top: 4px;
  color: #88d6c2;
  font-size: 9px;
  font-weight: 600;
}

.tool-strip {
  margin-top: 9px;
  display: grid;
  gap: 6px;
}

.tool-item {
  padding: 8px 9px;
  border-radius: 10px;
  background: rgba(60, 91, 147, 0.12);
}

.tool-title {
  display: flex;
  align-items: center;
  gap: 7px;
}

.tool-title > span {
  width: 17px;
  height: 17px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  background: rgba(104, 148, 235, 0.15);
  color: #9cb7ed;
  font-size: 8px;
}

.tool-title strong {
  font-size: 10px;
}

.tool-title small {
  margin-left: auto;
  color: #687fa9;
  font-size: 8px;
}

.tool-item p {
  margin: 6px 0 0 24px;
  color: #7890ba;
  font-size: 9px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-state {
  min-height: 430px;
  display: grid;
  place-items: center;
}

:deep(.el-button) {
  height: 34px;
  border-radius: 10px;
  border-color: rgba(159, 189, 249, 0.16);
  background: rgba(74, 111, 182, 0.10);
  color: #dce8ff;
  font-size: 11px;
}

:deep(.el-button:hover) {
  border-color: rgba(159, 189, 249, 0.28);
  background: rgba(78, 119, 202, 0.18);
  color: white;
}

:deep(.el-button--primary) {
  border: 0;
  color: white;
  background: linear-gradient(135deg, #4d8df5, #725ff0);
  box-shadow: 0 8px 20px rgba(82, 103, 232, 0.18);
}

:deep(.el-button--success) {
  border-color: rgba(82, 204, 162, 0.28);
  background: rgba(55, 177, 137, 0.13);
  color: #9ce6cc;
}

:deep(.el-button--danger) {
  border-color: rgba(241, 111, 126, 0.24);
  background: rgba(222, 73, 91, 0.08);
  color: #f3a3ad;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  min-height: 34px;
  border-radius: 10px;
  background: rgba(8, 28, 63, 0.6);
  box-shadow: 0 0 0 1px rgba(151, 183, 244, 0.12) inset !important;
}

:deep(.el-input__inner),
:deep(.el-select__placeholder),
:deep(.el-select__selected-item) {
  color: #d7e4fb;
  font-size: 11px;
}

:deep(.el-alert) {
  border: 1px solid rgba(94, 155, 255, 0.14);
  background: rgba(45, 103, 190, 0.10);
}

:deep(.el-alert__title) {
  color: #aac3ef;
  font-size: 10px;
}

:deep(.el-table) {
  --el-table-border-color: rgba(139, 171, 231, 0.08);
  --el-table-header-bg-color: rgba(17, 41, 82, 0.35);
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(83, 126, 206, 0.09);
  --el-table-text-color: #afbee0;
  --el-table-header-text-color: #6f84ad;
  background: transparent;
  font-size: 10px;
}

:deep(.el-table::before) {
  display: none;
}

:deep(.el-table th.el-table__cell),
:deep(.el-table td.el-table__cell) {
  padding: 7px 0;
}

:deep(.el-table .cell) {
  padding: 0 6px;
}

:deep(.el-table__inner-wrapper),
:deep(.el-table__body-wrapper),
:deep(.el-scrollbar__wrap),
:deep(.el-scrollbar__view) {
  background: transparent;
}

:deep(.el-tag) {
  border: 0;
  background: linear-gradient(135deg, #508ae8, #735fdc);
  font-size: 9px;
}

:deep(.el-empty__description p) {
  color: #687da7;
  font-size: 10px;
}

:deep(.el-empty__image) {
  opacity: 0.55;
}

@media (max-width: 1120px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-panel,
  .monitor-panel,
  .recommendation-panel,
  .audit-panel {
    grid-column: span 6;
  }
}

@media (max-width: 850px) {
  .app-shell {
    display: block;
    padding: 10px;
  }

  .sidebar {
    position: static;
    height: auto;
    margin-bottom: 10px;
    padding: 10px;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    border-radius: 18px;
  }

  .brand {
    padding: 0 8px 0 0;
    flex: 0 0 auto;
  }

  .brand span,
  .runtime-card,
  .sidebar-setting,
  .sidebar-spacer {
    display: none;
  }

  .nav-list {
    flex-direction: row;
  }

  .nav-item {
    flex: 0 0 auto;
    min-height: 36px;
  }

  .main-panel {
    padding: 16px;
    border-radius: 18px;
  }

  .topbar {
    flex-direction: column;
  }

  .toolbar {
    width: 100%;
    justify-content: flex-start;
  }

  .product-select {
    width: min(100%, 220px);
  }

  .chart-panel,
  .monitor-panel,
  .recommendation-panel,
  .audit-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 560px) {
  .summary-grid {
    grid-template-columns: 1fr 1fr;
  }

  .metric-card {
    min-height: 88px;
    padding: 11px;
  }

  .metric-icon {
    display: none;
  }

  .metric-copy strong {
    font-size: 18px;
  }

  .toolbar .el-button {
    flex: 1;
  }

  .product-select {
    width: 100%;
  }

  .decision-row {
    grid-template-columns: 1fr 1fr;
  }

  .decision-row .el-tag {
    grid-column: 1 / -1;
    justify-self: start;
  }

  .decision-actions {
    flex-direction: column;
  }

  .run-head {
    flex-direction: column;
  }

  .run-meta {
    text-align: left;
  }
}
</style>
