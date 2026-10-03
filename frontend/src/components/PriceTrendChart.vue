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
    animationDuration: 320,
    color: ['#416fd5', '#2fa07a', '#eaa246'],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(250,252,255,.98)',
      borderColor: '#dce6f1',
      padding: compact ? 7 : 9,
      textStyle: { color: '#24344f', fontSize: compact ? 10 : 11 },
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
      itemWidth: compact ? 12 : 15,
      itemHeight: 6,
      itemGap: compact ? 10 : 14,
      textStyle: { color: '#65748a', fontSize: compact ? 10 : 11 },
    },
    grid: { left: compact ? 42 : 46, right: 12, top: compact ? 34 : 38, bottom: 27 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: daily.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#dce5ef' } },
      axisTick: { show: false },
      axisLabel: { color: '#8491a3', fontSize: compact ? 9 : 10, margin: 9 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: compact ? '' : '价格 / ¥',
      nameTextStyle: { color: '#8996a8', fontSize: 10, padding: [0, 0, 4, -8] },
      axisLabel: { color: '#8491a3', fontSize: compact ? 9 : 10 },
      splitLine: { lineStyle: { color: '#e8eef5', type: 'dashed' } },
    },
    series: [
      {
        name: '我方价格',
        type: 'line',
        smooth: .35,
        symbol: 'circle',
        symbolSize: compact ? 4 : 5,
        connectNulls: false,
        lineStyle: { width: compact ? 2 : 2.3 },
        areaStyle: { opacity: .045 },
        data: daily.map((item) => item.own_price),
      },
      {
        name: '市场均价',
        type: 'line',
        smooth: .35,
        symbol: 'circle',
        symbolSize: compact ? 4 : 5,
        connectNulls: false,
        lineStyle: { width: 2 },
        data: daily.map((item) => item.competitor_avg_price),
      },
      {
        name: '市场最低价',
        type: 'line',
        smooth: .35,
        symbol: 'circle',
        symbolSize: compact ? 3 : 4,
        connectNulls: false,
        lineStyle: { width: 1.7, type: 'dashed' },
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
