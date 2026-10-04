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
    color: ['#2f6df6', '#875bea', '#20b97a'],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1c2739',
      borderWidth: 0,
      padding: compact ? 8 : 9,
      textStyle: { color: '#f7f9fc', fontSize: 11 },
      extraCssText: 'border-radius:9px;box-shadow:0 10px 28px rgba(17,28,45,.18)',
      formatter(params: any[]) {
        const title = params?.[0]?.axisValueLabel || ''
        const lines = params
          .filter((item) => item.value !== null && item.value !== undefined && item.value !== '-')
          .map((item) => `${item.marker}${item.seriesName}　<b>¥${Number(item.value).toFixed(2)}</b>`)
        return [title, ...lines].join('<br/>')
      },
    },
    legend: {
      top: 0,
      right: 2,
      itemWidth: compact ? 13 : 16,
      itemHeight: 7,
      itemGap: compact ? 11 : 15,
      textStyle: { color: '#6b7890', fontSize: 10.5 },
    },
    grid: { left: compact ? 44 : 48, right: 12, top: compact ? 34 : 38, bottom: 25 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: daily.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#8290a3', fontSize: 10, margin: 8 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: compact ? '' : '价格 / ¥',
      nameTextStyle: { color: '#8d99aa', fontSize: 10.5, padding: [0, 0, 4, -6] },
      axisLabel: { color: '#8290a3', fontSize: 10 },
      splitLine: { lineStyle: { color: '#edf1f6', type: 'solid' } },
    },
    series: [
      {
        name: '我方价格', type: 'line', smooth: .32, symbol: 'circle', symbolSize: compact ? 5 : 6, connectNulls: false,
        lineStyle: { width: compact ? 2.2 : 2.6 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(47,109,246,.16)' }, { offset: 1, color: 'rgba(47,109,246,.01)' }]) },
        data: daily.map((item) => item.own_price),
      },
      {
        name: '市场均价', type: 'line', smooth: .32, symbol: 'circle', symbolSize: compact ? 5 : 6, connectNulls: false,
        lineStyle: { width: 2 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(135,91,234,.09)' }, { offset: 1, color: 'rgba(135,91,234,0)' }]) },
        data: daily.map((item) => item.competitor_avg_price),
      },
      {
        name: '市场最低价', type: 'line', smooth: .32, symbol: 'circle', symbolSize: compact ? 4 : 5, connectNulls: false,
        lineStyle: { width: 1.8 },
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

<template><div ref="el" class="trend-chart" :style="{ height: `${height}px` }" /></template>
<style scoped>.trend-chart { width: 100%; min-width: 0; }</style>
