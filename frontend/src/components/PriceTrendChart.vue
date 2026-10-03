<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { TrendPayload } from '../types'

const props = withDefaults(defineProps<{
  trend: TrendPayload | null
  height?: number
  compact?: boolean
}>(), { height: 330, compact: false })

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function draw() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  const daily = props.trend?.daily || []
  chart.setOption({
    animationDuration: 400,
    color: ['#3f6fd8', '#33a77b', '#f0a84a'],
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,.98)',
      borderColor: '#dfe7f1',
      textStyle: { color: '#24344f', fontSize: 12 },
      formatter(params: any[]) {
        const title = params?.[0]?.axisValueLabel || ''
        const lines = params
          .filter((item) => item.value !== null && item.value !== undefined && item.value !== '-')
          .map((item) => `${item.marker}${item.seriesName}：¥${Number(item.value).toFixed(2)}`)
        return [title, ...lines].join('<br/>')
      },
    },
    legend: {
      top: 2,
      right: 0,
      itemWidth: 18,
      itemHeight: 8,
      textStyle: { color: '#65748a', fontSize: props.compact ? 11 : 12 },
    },
    grid: { left: 52, right: 18, top: 48, bottom: 35 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: daily.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#dbe4ef' } },
      axisTick: { show: false },
      axisLabel: { color: '#8390a3', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '价格 / ¥',
      nameTextStyle: { color: '#8996a8', fontSize: 11, padding: [0, 0, 6, -12] },
      axisLabel: { color: '#8390a3', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e9eef5' } },
    },
    series: [
      {
        name: '我方价格',
        type: 'line',
        smooth: .35,
        symbol: 'circle',
        symbolSize: 6,
        connectNulls: false,
        lineStyle: { width: 2.6 },
        areaStyle: { opacity: .05 },
        data: daily.map((item) => item.own_price),
      },
      {
        name: '市场均价',
        type: 'line',
        smooth: .35,
        symbol: 'circle',
        symbolSize: 6,
        connectNulls: false,
        lineStyle: { width: 2.4 },
        data: daily.map((item) => item.competitor_avg_price),
      },
      {
        name: '市场最低价',
        type: 'line',
        smooth: .35,
        symbol: 'circle',
        symbolSize: 5,
        connectNulls: false,
        lineStyle: { width: 2, type: 'dashed' },
        data: daily.map((item) => item.competitor_min_price),
      },
    ],
  }, true)
  chart.resize()
}

function handleResize() { chart?.resize() }

watch(() => props.trend, () => nextTick(draw), { deep: true })
onMounted(() => { draw(); window.addEventListener('resize', handleResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); chart?.dispose(); chart = null })
</script>

<template>
  <div ref="el" class="trend-chart" :style="{ height: `${height}px` }" />
</template>

<style scoped>
.trend-chart { width: 100%; min-width: 0; }
</style>
