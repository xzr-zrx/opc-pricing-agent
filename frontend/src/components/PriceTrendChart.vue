<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { TrendPayload } from '../types'

const props = withDefaults(defineProps<{
  trend: TrendPayload | null
  height?: number
  compact?: boolean
}>(), { height: 250, compact: false })

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function draw() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  const daily = props.trend?.daily || []
  const compact = props.compact
  chart.setOption({
    animationDuration: 260,
    color: ['#3568d4', '#2f8f68', '#d28a32'],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#dfe6ee',
      padding: compact ? 8 : 9,
      textStyle: { color: '#27364b', fontSize: 11 },
      formatter(params: any[]) {
        const title = params?.[0]?.axisValueLabel || ''
        const lines = params
          .filter((item) => item.value !== null && item.value !== undefined && item.value !== '-')
          .map((item) => `${item.marker}${item.seriesName}：¥${Number(item.value).toFixed(2)}`)
        return [title, ...lines].join('<br/>')
      },
    },
    legend: {
      top: 0,
      right: 2,
      itemWidth: compact ? 13 : 16,
      itemHeight: 7,
      itemGap: compact ? 11 : 15,
      textStyle: { color: '#65748a', fontSize: 11 },
    },
    grid: { left: compact ? 46 : 50, right: 14, top: compact ? 34 : 38, bottom: 28 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: daily.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#dfe5ec' } },
      axisTick: { show: false },
      axisLabel: { color: '#7f8b9a', fontSize: 11, margin: 9 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: compact ? '' : '价格 / ¥',
      nameTextStyle: { color: '#8290a2', fontSize: 11, padding: [0, 0, 4, -6] },
      axisLabel: { color: '#7f8b9a', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e8edf3', type: 'dashed' } },
    },
    series: [
      {
        name: '我方价格',
        type: 'line',
        smooth: .25,
        symbol: 'circle',
        symbolSize: compact ? 5 : 6,
        connectNulls: false,
        lineStyle: { width: compact ? 2.2 : 2.6 },
        data: daily.map((item) => item.own_price),
      },
      {
        name: '市场均价',
        type: 'line',
        smooth: .25,
        symbol: 'circle',
        symbolSize: compact ? 5 : 6,
        connectNulls: false,
        lineStyle: { width: 2.2 },
        data: daily.map((item) => item.competitor_avg_price),
      },
      {
        name: '市场最低价',
        type: 'line',
        smooth: .25,
        symbol: 'circle',
        symbolSize: compact ? 4 : 5,
        connectNulls: false,
        lineStyle: { width: 1.8, type: 'dashed' },
        data: daily.map((item) => item.competitor_min_price),
      },
    ],
  }, true)
  chart.resize()
}

function handleResize() { chart?.resize() }

watch(() => props.trend, () => nextTick(draw), { deep: true })
watch(() => props.height, () => nextTick(draw))
onMounted(() => { draw(); window.addEventListener('resize', handleResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); chart?.dispose(); chart = null })
</script>

<template>
  <div ref="el" class="trend-chart" :style="{ height: `${height}px` }" />
</template>

<style scoped>
.trend-chart { width: 100%; min-width: 0; }
</style>
