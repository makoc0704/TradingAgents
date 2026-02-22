// Shared TypeScript interfaces mirroring backend Pydantic schemas

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
}

export interface TaskStatus {
  task_id: string;
  task_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress_percent: number;
  message: string;
  created_at: string;
  result: Record<string, unknown> | null;
}

export interface RiskMetrics {
  ticker: string;
  date: string;
  daily_volatility: number;
  annualized_volatility: number;
  atr: number;
  atr_percent: number;
  max_drawdown: number;
  current_drawdown: number;
  var_95: number;
  var_99: number;
  cvar_95: number;
  beta: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  current_price: number;
  sma_50: number;
  sma_200: number;
  rsi: number;
}

export interface TradeRecord {
  date: string;
  ticker: string;
  action: string;
  price: number;
  shares: number;
  commission: number;
  portfolio_value: number;
  cash: number;
  position_value: number;
}

export interface DailySnapshot {
  date: string;
  portfolio_value: number;
  cash: number;
  position_shares: number;
  position_value: number;
  daily_return: number;
  cumulative_return: number;
  action: string;
}

export interface BacktestResult {
  config: Record<string, unknown>;
  trades: TradeRecord[];
  daily_snapshots: DailySnapshot[];
  performance: Record<string, number>;
  total_trading_days: number;
  total_trades: number;
}

export interface Position {
  ticker: string;
  shares: number;
  avg_entry_price: number;
  current_price: number;
  target_weight: number;
  actual_weight: number;
  market_value: number;
}

export interface PortfolioSnapshot {
  date: string;
  total_value: number;
  cash: number;
  positions: Record<string, Position>;
  allocation: {
    weights: Record<string, number>;
    method: string;
    portfolio_volatility: number;
    portfolio_var_95: number;
    diversification_ratio: number;
  } | null;
  daily_return: number;
  cumulative_return: number;
  actions: Record<string, string>;
}

export interface PortfolioResult {
  config: Record<string, unknown>;
  snapshots: PortfolioSnapshot[];
  all_trades: Record<string, unknown>[];
  performance: Record<string, number>;
  per_ticker_performance: Record<string, Record<string, number>>;
  total_trading_days: number;
  total_trades: number;
}

export interface PipelineJob {
  job_name: string;
  job_type: string;
  enabled: boolean;
  cron_expression: string;
  next_run: string | null;
  last_status: string | null;
  last_signal: string | null;
  last_run_at: string | null;
  last_duration_seconds: number | null;
}

export interface PipelineStatus {
  running: boolean;
  total_jobs: number;
  enabled_jobs: number;
  jobs: PipelineJob[];
}

export interface AnalysisResult {
  ticker: string;
  date: string;
  final_decision: string;
  signal: string;
  confidence: string;
  market_report: string;
  sentiment_report: string;
  news_report: string;
  fundamentals_report: string;
  risk_metrics: Record<string, unknown> | null;
  investment_debate: DebateState | null;
  risk_debate: DebateState | null;
}

// --- Live Trading ---

export interface LivePosition {
  ticker: string;
  shares: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  weight: number;
}

export interface LivePortfolio {
  total_value: number;
  cash: number;
  initial_capital: number;
  positions: LivePosition[];
  total_return: number;
  daily_return: number;
  last_updated: string;
}

export interface LiveTrade {
  date: string;
  ticker: string;
  action: string;
  price: number;
  shares: number;
  commission: number;
}

export interface LivePerformance {
  total_return: number;
  daily_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  trading_days: number;
}

export interface LiveRunSnapshot {
  date: string;
  portfolio_value: number;
  daily_return: number;
  cumulative_return: number;
}

// --- Agent Flow / Debate ---

export interface DebateArgument {
  role: string;
  content: string;
  round?: number;
}

export interface DebateState {
  bull_arguments?: DebateArgument[];
  bear_arguments?: DebateArgument[];
  judge_verdict?: string;
  rounds?: number;
  [key: string]: unknown;
}

// --- History ---

export interface HistoryEntry {
  ticker: string;
  date: string;
  signal: string;
  confidence: string;
  has_debate: boolean;
}
