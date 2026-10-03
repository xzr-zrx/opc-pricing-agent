<script setup lang="ts">
import {computed,onMounted,ref} from 'vue'
import * as echarts from 'echarts'
import {api} from './api/client'

type Product={id:number,name:string,cost:number,current_price:number,min_margin_rate:number,stock:number}
type Competitor={id:number,name:string,source_type:string,mock_index:number}
const products=ref<Product[]>([]),selectedId=ref<number|null>(null),competitors=ref<Competitor[]>([]),history=ref<any[]>([]),recs=ref<any[]>([]),runs=ref<any[]>([])
const selected=computed(()=>products.value.find(x=>x.id===selectedId.value)||null)
const busy=ref(false),message=ref('')

async function loadProducts(){products.value=(await api.get('/products')).data;if(!selectedId.value&&products.value.length) selectedId.value=products.value[0].id;if(selectedId.value) await loadDetail()}
async function loadDetail(){if(!selectedId.value)return;const id=selectedId.value;const [c,h,r,u]=await Promise.all([api.get(`/products/${id}/competitors`),api.get(`/products/${id}/price-history`),api.get(`/products/${id}/recommendations`),api.get(`/products/${id}/runs`)]);competitors.value=c.data;history.value=h.data;recs.value=r.data;runs.value=u.data;setTimeout(drawChart,50)}
async function seed(){busy.value=true;try{const r=await api.post('/demo/seed');selectedId.value=r.data.product_id;await loadProducts();message.value='Demo 数据已初始化'}finally{busy.value=false}}
async function advance(){if(!selectedId.value)return;busy.value=true;try{const r=await api.post(`/demo/products/${selectedId.value}/advance`);message.value='Mock 场景已推进：'+JSON.stringify(r.data.results);await loadDetail()}finally{busy.value=false}}
async function analyze(){if(!selectedId.value)return;busy.value=true;try{await api.post(`/products/${selectedId.value}/analyze`);message.value='Agent 分析完成';await loadDetail()}finally{busy.value=false}}
async function testLLM(){busy.value=true;try{const r=await api.post('/settings/llm/test');message.value=JSON.stringify(r.data)}finally{busy.value=false}}
async function accept(id:number){await api.post(`/recommendations/${id}/accept`);await loadDetail()}
async function reject(id:number){await api.post(`/recommendations/${id}/reject`);await loadDetail()}
function drawChart(){const el=document.getElementById('priceChart');if(!el)return;const chart=echarts.init(el);const x=Array.from(new Set(history.value.flatMap((h:any)=>h.points.map((p:any)=>p.time.slice(11,19)))));chart.setOption({tooltip:{trigger:'axis'},legend:{},xAxis:{type:'category',data:x},yAxis:{type:'value',name:'价格'},series:history.value.map((h:any)=>({name:h.name,type:'line',smooth:true,data:h.points.map((p:any)=>p.price)}))})}
onMounted(loadProducts)
</script>

<template>
<div class="page">
  <div class="topbar"><div><h1>OPC 竞品监测与智能定价 Agent</h1><p>监控 → 事件 → Agent 工具调用 → 建议 → 人工确认</p></div><div class="actions"><el-button @click="testLLM">测试 LLM</el-button><el-button type="primary" :loading="busy" @click="seed">初始化 Demo</el-button></div></div>
  <el-alert v-if="message" :title="message" type="info" show-icon :closable="true" @close="message=''"/>
  <div class="grid" v-if="selected">
    <el-card class="hero"><template #header><div class="card-head"><span>{{selected.name}}</span><el-select v-model="selectedId" style="width:220px" @change="loadDetail"><el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id"/></el-select></div></template>
      <div class="stats"><div><b>¥{{selected.current_price}}</b><span>当前售价</span></div><div><b>¥{{selected.cost}}</b><span>成本</span></div><div><b>{{Math.round(selected.min_margin_rate*100)}}%</b><span>最低毛利率</span></div><div><b>{{selected.stock}}</b><span>库存</span></div></div>
      <div class="hero-actions"><el-button type="warning" :loading="busy" @click="advance">推进 Mock 场景</el-button><el-button type="success" :loading="busy" @click="analyze">立即分析</el-button></div>
    </el-card>

    <el-card><template #header>竞品价格历史</template><div id="priceChart" style="height:320px"></div></el-card>

    <el-card><template #header>竞品监控</template><el-table :data="competitors"><el-table-column prop="name" label="竞品"/><el-table-column prop="source_type" label="来源"/><el-table-column prop="mock_index" label="场景阶段"/></el-table></el-card>

    <el-card><template #header>最新定价建议</template>
      <div v-if="recs.length" class="recommendation">
        <div class="rec-title"><el-tag size="large">{{recs[0].action}}</el-tag><strong v-if="recs[0].suggested_price">建议价 ¥{{recs[0].suggested_price}}</strong><span>数据完整度 {{recs[0].data_completeness}}</span></div>
        <h4>证据</h4><ul><li v-for="e in recs[0].evidence_summary" :key="e">{{e}}</li></ul>
        <h4>风险</h4><ul><li v-for="e in recs[0].risk_notes" :key="e">{{e}}</li></ul>
        <div><el-button type="success" @click="accept(recs[0].id)">接受建议</el-button><el-button type="danger" plain @click="reject(recs[0].id)">拒绝建议</el-button><span class="status">状态：{{recs[0].status}}</span></div>
      </div><el-empty v-else description="尚无建议，先推进场景并分析"/>
    </el-card>

    <el-card class="audit"><template #header>Agent Run 审计时间线</template>
      <el-timeline v-if="runs.length">
        <el-timeline-item v-for="run in runs" :key="run.id" :timestamp="run.started_at" placement="top">
          <el-card><div class="run-head"><b>Run #{{run.id}} · {{run.status}}</b><span>{{run.provider}} / {{run.model}}</span></div>
          <div v-for="(t,i) in run.tool_calls" :key="i" class="tool"><el-tag type="info">{{i+1}}. {{t.tool_name}}</el-tag><span>{{t.duration_ms}} ms</span><pre>{{t.result_summary}}</pre></div></el-card>
        </el-timeline-item>
      </el-timeline><el-empty v-else description="暂无 Agent Run"/>
    </el-card>
  </div>
  <el-empty v-else description="点击右上角初始化 Demo 数据"/>
</div>
</template>

<style scoped>
:global(body){margin:0;background:#f4f7fb;color:#1f2937;font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif}.page{max-width:1280px;margin:auto;padding:28px}.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}.topbar h1{margin:0 0 6px;font-size:28px}.topbar p{margin:0;color:#6b7280}.actions{display:flex;gap:10px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.hero,.audit{grid-column:1/-1}.card-head,.run-head,.rec-title{display:flex;justify-content:space-between;align-items:center;gap:12px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.stats div{padding:18px;background:#f8fafc;border-radius:12px}.stats b{display:block;font-size:24px;margin-bottom:4px}.stats span,.status,.run-head span{color:#6b7280}.hero-actions{margin-top:18px}.recommendation ul{padding-left:20px}.tool{margin-top:12px;border-top:1px solid #eee;padding-top:10px}.tool span{margin-left:10px;color:#6b7280}.tool pre{white-space:pre-wrap;background:#f8fafc;padding:10px;border-radius:8px;max-height:150px;overflow:auto;font-size:12px}@media(max-width:850px){.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}.topbar{align-items:flex-start;gap:16px;flex-direction:column}.hero,.audit{grid-column:1}}
</style>
