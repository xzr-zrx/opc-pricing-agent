<script setup lang="ts">
import type { AgentRun } from '../types'

defineProps<{ runs: AgentRun[] }>()

function formatTime(value?: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="page-stack">
    <section class="hero-card">
      <div><span class="kicker">运行记录</span><h2>运行审计</h2><p>每次 Agent Run 的工具调用、数据来源、耗时和最终结果。</p></div>
      <span class="count-chip">{{ runs.length }} 次运行</span>
    </section>

    <section class="surface-card">
      <el-collapse v-if="runs.length" accordion>
        <el-collapse-item v-for="run in runs" :key="run.id" :name="run.id">
          <template #title>
            <div class="run-title">
              <div><strong>Run #{{ run.id }}</strong><span>{{ formatTime(run.started_at) }}</span></div>
              <div class="run-tags"><el-tag :type="run.status === 'succeeded' ? 'success' : run.status === 'failed' ? 'danger' : 'info'" effect="light">{{ run.status }}</el-tag><span>{{ run.provider }} / {{ run.model }}</span><b>{{ run.step_count }} steps</b></div>
            </div>
          </template>
          <div class="run-body">
            <div v-if="run.recommendation" class="result-card">
              <div><span>最终建议</span><strong>{{ run.recommendation.strategy || run.recommendation.action }} · ¥{{ run.recommendation.suggested_price ?? '—' }}</strong></div>
              <p>{{ run.recommendation.summary || run.recommendation.evidence_summary?.[0] }}</p>
            </div>
            <div class="tool-list">
              <article v-for="(tool, index) in run.tool_calls" :key="`${run.id}-${index}`" class="tool-card">
                <div class="tool-head"><span>{{ index + 1 }}</span><strong>{{ tool.tool_name }}</strong><small>{{ tool.duration_ms }} ms · {{ tool.success ? 'success' : 'failed' }}</small></div>
                <div class="tool-grid"><div><label>Arguments</label><pre>{{ JSON.stringify(tool.arguments, null, 2) }}</pre></div><div><label>Result summary</label><pre>{{ tool.result_summary || '无结果摘要' }}</pre></div></div>
              </article>
            </div>
            <div v-if="run.error" class="error-box">{{ run.error }}</div>
          </div>
        </el-collapse-item>
      </el-collapse>
      <div v-else class="empty-block">暂无 Agent 运行记录。</div>
    </section>
  </div>
</template>

<style scoped>
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto minmax(0,1fr); gap:8px; }
.hero-card,.surface-card { border:1px solid #dfe6ee; background:#fff; border-radius:11px; }
.hero-card { padding:9px 13px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#6178a2; font-size:11px; font-weight:700; }
h2 { margin:2px 0; color:#1c2b3f; font-size:18px; }
.hero-card p { margin:0; color:#7f8b9a; font-size:11px; }
.count-chip { border:1px solid #dfe6ee; background:#f7f9fc; color:#647286; border-radius:7px; padding:6px 9px; font-size:11px; }
.surface-card { min-height:0; padding:6px 12px; overflow:auto; scrollbar-width:thin; scrollbar-color:#cbd5e1 transparent; }
.run-title { width:100%; padding-right:12px; display:flex; justify-content:space-between; gap:14px; align-items:center; }
.run-title strong,.run-title span { display:block; }
.run-title strong { color:#2d3d56; font-size:12px; }
.run-title span { margin-top:1px; color:#8793a2; font-size:10.5px; }
.run-tags { display:flex; gap:7px; align-items:center; }
.run-tags span { margin:0; color:#6f7e93; font-size:10.5px; }
.run-tags b { font-size:10.5px; color:#53647f; }
.run-body { padding:4px 1px 8px; }
.result-card { padding:8px 10px; border-radius:8px; background:#f6f9fd; border:1px solid #e1e8f0; display:grid; grid-template-columns:210px 1fr; gap:10px; align-items:center; }
.result-card span,.result-card strong { display:block; }
.result-card span { color:#7f8b9a; font-size:10.5px; }
.result-card strong { margin-top:2px; color:#284f9b; font-size:12px; }
.result-card p { margin:0; color:#617086; font-size:11px; line-height:1.35; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tool-list { margin-top:7px; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px; }
.tool-card { padding:8px; border:1px solid #e4e9ef; border-radius:8px; background:#fbfcfd; min-width:0; }
.tool-head { display:flex; align-items:center; gap:6px; }
.tool-head>span { width:20px; height:20px; display:grid; place-items:center; border-radius:5px; background:#eef4ff; color:#4e6fae; font-size:10.5px; }
.tool-head strong { color:#35465f; font-size:11px; }
.tool-head small { margin-left:auto; color:#8290a2; font-size:10.5px; }
.tool-grid { margin-top:6px; display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.tool-grid label { display:block; margin-bottom:3px; color:#8491a1; font-size:10.5px; }
.tool-grid pre { margin:0; max-height:78px; overflow:auto; padding:6px; border-radius:6px; background:#f2f5f8; color:#566579; font:10.5px/1.35 ui-monospace,SFMono-Regular,Consolas,monospace; white-space:pre-wrap; word-break:break-word; }
.error-box { margin-top:6px; padding:7px; border-radius:7px; background:#fff1f2; color:#a34f59; font-size:11px; }
.empty-block { height:100%; min-height:240px; display:grid; place-items:center; color:#8995a4; font-size:12px; }
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.surface-card{overflow:visible}.tool-list{grid-template-columns:1fr}}
@media(max-width:800px){.run-title,.run-tags{align-items:flex-start;flex-direction:column}.tool-grid,.result-card{grid-template-columns:1fr}}
</style>
