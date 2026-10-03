export type Product = {
  id: number
  name: string
  sku?: string | null
  search_keyword?: string | null
  cost: number
  current_price: number
  min_margin_rate: number
  stock: number
}

export type Competitor = {
  id: number
  name: string
  source_type: string
  active: boolean
}

export type MarketplaceItem = {
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

export type MarketplacePayload = {
  product_id: number
  keyword: string
  source: string
  provider_name?: string
  queried_at: string | null
  count: number
  notice?: string | null
  items: MarketplaceItem[]
}

export type TrendDaily = {
  date: string
  own_price: number | null
  own_price_observed: boolean
  competitor_avg_price: number | null
  competitor_min_price: number | null
  competitor_max_price: number | null
  competitor_count: number
  competitor_sales_total: number | null
}

export type TrendSummary = {
  current_price: number
  period_market_avg_price: number | null
  period_market_min_price: number | null
  period_market_max_price: number | null
  first_market_avg_price: number | null
  latest_market_avg_price: number | null
  trend_percent: number | null
  trend: 'up' | 'down' | 'stable' | 'insufficient' | string
  market_data_days: number
  own_observed_days: number
  competitor_samples: number
}

export type TrendPayload = {
  product_id: number
  start_date: string
  end_date: string
  days: number
  mode: 'real' | 'demo'
  source: string
  source_label: string
  history_insufficient: boolean
  notice: string
  summary: TrendSummary
  daily: TrendDaily[]
}

export type Recommendation = {
  id: number
  run_id: number
  action: string
  suggested_price: number | null
  strategy?: string | null
  summary?: string | null
  confidence?: number | null
  risk_level?: string | null
  analysis_window?: { start_date?: string; end_date?: string } | null
  key_metrics?: Record<string, any>
  promotion?: Record<string, any>
  evidence_summary: string[]
  risk_notes: string[]
  data_completeness: 'HIGH' | 'MEDIUM' | 'LOW' | string
  next_check_after_hours: number
  need_user_inputs: string[]
  status: string
  created_at: string
}

export type AgentRun = {
  id: number
  status: string
  provider: string
  model: string
  step_count: number
  started_at: string
  finished_at?: string | null
  error?: string | null
  recommendation?: Recommendation | null
  tool_calls: Array<{
    tool_name: string
    arguments: Record<string, any>
    result_summary?: string | null
    success: boolean
    duration_ms: number
  }>
}

export type ViewKey = 'overview' | 'competitors' | 'trends' | 'pricing' | 'audit'
