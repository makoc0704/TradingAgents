// Typed API client for the TradingAgents backend

import type {
  ApiResponse,
  TaskStatus,
  RiskMetrics,
  PipelineStatus,
  AnalysisResult,
} from "../types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  return res.json();
}

// --- Analysis ---

export async function runAnalysis(body: {
  ticker: string;
  analysis_date: string;
  selected_analysts?: string[];
  llm_provider?: string;
}): Promise<ApiResponse<TaskStatus>> {
  return fetchJson("/analysis/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getAnalysisStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
  return fetchJson(`/analysis/status/${taskId}`);
}

export async function getAnalysisResult(
  ticker: string,
  date: string
): Promise<ApiResponse<AnalysisResult>> {
  return fetchJson(`/analysis/${ticker}/${date}`);
}

// --- Backtest ---

export async function runBacktest(body: {
  ticker: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  backtest_profile?: string;
  reflection_mode?: string;
}): Promise<ApiResponse<TaskStatus>> {
  return fetchJson("/backtest/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getBacktestStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
  return fetchJson(`/backtest/status/${taskId}`);
}

export async function getBacktestResult(taskId: string): Promise<ApiResponse<unknown>> {
  return fetchJson(`/backtest/result/${taskId}`);
}

// --- Portfolio ---

export async function runPortfolio(body: {
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital?: number;
  weighting_strategy?: string;
  backtest_profile?: string;
}): Promise<ApiResponse<TaskStatus>> {
  return fetchJson("/portfolio/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getPortfolioStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
  return fetchJson(`/portfolio/status/${taskId}`);
}

export async function getPortfolioResult(taskId: string): Promise<ApiResponse<unknown>> {
  return fetchJson(`/portfolio/result/${taskId}`);
}

// --- Pipeline ---

export async function getPipelineStatus(): Promise<ApiResponse<PipelineStatus>> {
  return fetchJson("/pipeline/status");
}

export async function getJobHistory(
  jobName: string,
  limit = 30
): Promise<ApiResponse<unknown[]>> {
  return fetchJson(`/pipeline/jobs/${jobName}/history?limit=${limit}`);
}

export async function getJobLatest(jobName: string): Promise<ApiResponse<unknown>> {
  return fetchJson(`/pipeline/jobs/${jobName}/latest`);
}

export async function runPipelineJob(jobName: string): Promise<ApiResponse<unknown>> {
  return fetchJson(`/pipeline/run-now/${jobName}`, { method: "POST" });
}

// --- Risk ---

export async function getRiskMetrics(
  ticker: string,
  date: string
): Promise<ApiResponse<RiskMetrics>> {
  return fetchJson(`/risk/${ticker}/${date}`);
}

// --- Results ---

export async function listTickers(): Promise<ApiResponse<string[]>> {
  return fetchJson("/results/tickers");
}

export async function listTickerDates(ticker: string): Promise<ApiResponse<string[]>> {
  return fetchJson(`/results/tickers/${ticker}/dates`);
}

export async function listPipelineJobs(): Promise<ApiResponse<string[]>> {
  return fetchJson("/results/pipeline/jobs");
}

// --- Health ---

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/health`);
  return res.json();
}
