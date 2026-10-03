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
      <div><span class="kicker">EXECUTION AUDIT</span><h2>运行审计</h2><p>查看每次 Agent Run 的工具调用、数据来源、耗时和最终结果。</p></div>
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
              <span>最终建议</span>
              <strong>{{ run.recommendation.strategy || run.recommendation.action }} · ¥{{ run.recommendation.suggested_price ?? '—' }}</strong>
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
.page-stack{display:grid;gap:18px}.hero-card,.surface-card{border:1px solid #dfe7f1;background:rgba(255,255,255,.92);border-radius:20px;box-shadow:0 12px 34px rgba(39,65,102,.06)}.hero-card{padding:22px 24px;display:flex;align-items:center;justify-content:space-between;gap:18px}.kicker{color:#5c79c6;font-size:11px;font-weight:800;letter-spacing:.14em}h2{margin:5px 0;color:#182741;font-size:26px}.hero-card p{margin:0;color:#8794a7;font-size:13px}.count-chip{border:1px solid #dce5f2;background:#f6f9fd;color:#63738b;border-radius:999px;padding:8px 12px;font-size:12px}.surface-card{padding:14px 22px}.run-title{width:100%;padding-right:18px;display:flex;justify-content:space-between;gap:20px;align-items:center}.run-title strong,.run-title span{display:block}.run-title strong{color:#2d3d56;font-size:14px}.run-title span{margin-top:3px;color:#939eae;font-size:11px}.run-tags{display:flex;gap:10px;align-items:center}.run-tags span{margin:0;color:#728096;font-size:11px}.run-tags b{font-size:11px;color:#53647f}.run-body{padding:4px 2px 12px}.result-card{padding:14px 16px;border-radius:14px;background:#f3f7fd;border:1px solid #e0e8f4}.result-card span,.result-card strong{display:block}.result-card span{color:#8491a3;font-size:11px}.result-card strong{margin-top:4px;color:#284b91;font-size:16px}.result-card p{margin:6px 0 0;color:#65748a;font-size:12px;line-height:1.6}.tool-list{margin-top:12px;display:grid;gap:10px}.tool-card{padding:14px;border:1px solid #e4eaf2;border-radius:14px;background:#fbfcfe}.tool-head{display:flex;align-items:center;gap:8px}.tool-head>span{width:23px;height:23px;display:grid;place-items:center;border-radius:7px;background:#eaf1fc;color:#4e6fae;font-size:11px}.tool-head strong{color:#35465f;font-size:13px}.tool-head small{margin-left:auto;color:#8b98aa;font-size:10px}.tool-grid{margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:10px}.tool-grid label{display:block;margin-bottom:5px;color:#8d99a9;font-size:10px}.tool-grid pre{margin:0;max-height:180px;overflow:auto;padding:10px;border-radius:10px;background:#f3f6fa;color:#5d6a7c;font:11px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre-wrap;word-break:break-word}.error-box{margin-top:10px;padding:10px;border-radius:10px;background:#fff1f2;color:#a34f59;font-size:12px}.empty-block{min-height:300px;display:grid;place-items:center;color:#919cac;font-size:13px}@media(max-width:800px){.run-title,.run-tags{align-items:flex-start;flex-direction:column}.tool-grid{grid-template-columns:1fr}}
</style>
