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
      <div><span class="kicker">EXECUTION AUDIT</span><h2>运行审计</h2><p>每次 Agent Run 的工具调用、数据来源、耗时和最终结果。</p></div>
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
.page-stack { height:100%; min-height:0; display:grid; grid-template-rows:auto minmax(0,1fr); gap:9px; }
.hero-card,.surface-card { border:1px solid rgba(218,228,241,.96); background:linear-gradient(145deg,rgba(253,254,255,.96),rgba(246,249,253,.94)); border-radius:16px; box-shadow:0 9px 24px rgba(42,72,110,.055), inset 0 1px 0 rgba(255,255,255,.86); }
.hero-card { padding:11px 15px; display:flex; align-items:center; justify-content:space-between; gap:14px; }
.kicker { color:#5d79c5; font-size:9px; font-weight:800; letter-spacing:.13em; }
h2 { margin:2px 0; color:#182741; font-size:18px; }
.hero-card p { margin:0; color:#8794a7; font-size:9.5px; }
.count-chip { border:1px solid #dce5f2; background:#f4f8fc; color:#63738b; border-radius:999px; padding:6px 9px; font-size:10px; }
.surface-card { min-height:0; padding:6px 14px; overflow:auto; scrollbar-width:thin; scrollbar-color:#cbd7e6 transparent; }
.run-title { width:100%; padding-right:12px; display:flex; justify-content:space-between; gap:14px; align-items:center; }
.run-title strong,.run-title span { display:block; }
.run-title strong { color:#2d3d56; font-size:11px; }
.run-title span { margin-top:1px; color:#939eae; font-size:9px; }
.run-tags { display:flex; gap:7px; align-items:center; }
.run-tags span { margin:0; color:#728096; font-size:9px; }
.run-tags b { font-size:9px; color:#53647f; }
.run-body { padding:3px 1px 7px; }
.result-card { padding:8px 10px; border-radius:10px; background:#f1f6fc; border:1px solid #dee8f4; display:grid; grid-template-columns:200px 1fr; gap:10px; align-items:center; }
.result-card span,.result-card strong { display:block; }
.result-card span { color:#8491a3; font-size:8.5px; }
.result-card strong { margin-top:2px; color:#284b91; font-size:11px; }
.result-card p { margin:0; color:#65748a; font-size:9.5px; line-height:1.35; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tool-list { margin-top:7px; display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px; }
.tool-card { padding:8px; border:1px solid #e4eaf2; border-radius:10px; background:rgba(249,251,253,.92); min-width:0; }
.tool-head { display:flex; align-items:center; gap:6px; }
.tool-head>span { width:19px; height:19px; display:grid; place-items:center; border-radius:6px; background:#e8f0fb; color:#4e6fae; font-size:8.5px; }
.tool-head strong { color:#35465f; font-size:10px; }
.tool-head small { margin-left:auto; color:#8b98aa; font-size:8px; }
.tool-grid { margin-top:6px; display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.tool-grid label { display:block; margin-bottom:3px; color:#8d99a9; font-size:8px; }
.tool-grid pre { margin:0; max-height:72px; overflow:auto; padding:6px; border-radius:7px; background:#f1f5f9; color:#5d6a7c; font:8.5px/1.35 ui-monospace,SFMono-Regular,Consolas,monospace; white-space:pre-wrap; word-break:break-word; }
.error-box { margin-top:6px; padding:7px; border-radius:8px; background:#fff1f2; color:#a34f59; font-size:9px; }
.empty-block { height:100%; min-height:240px; display:grid; place-items:center; color:#919cac; font-size:11px; }
@media(max-width:980px){.page-stack{height:auto;grid-template-rows:auto}.surface-card{overflow:visible}.tool-list{grid-template-columns:1fr}}
@media(max-width:800px){.run-title,.run-tags{align-items:flex-start;flex-direction:column}.tool-grid,.result-card{grid-template-columns:1fr}}
</style>
