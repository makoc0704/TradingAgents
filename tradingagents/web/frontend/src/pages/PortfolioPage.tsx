import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import ProgressBar from "../components/common/ProgressBar";
import { SkeletonCard } from "../components/common/Skeleton";
import TradingChart from "../components/charts/TradingChart";
import { runPortfolio, getPortfolioResult } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import { formatPercent, formatCurrency } from "../utils/format";
import type { TaskStatus, PortfolioResult } from "../types";
import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];

export default function PortfolioPage() {
  const [tickersInput, setTickersInput] = useState("NVDA, AAPL, MSFT");
  const [startDate, setStartDate] = useState("2024-06-03");
  const [endDate, setEndDate] = useState("2024-06-07");
  const [strategy, setStrategy] = useState("equal");
  const [capital, setCapital] = useState(100000);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<PortfolioResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRunning = task?.status === "running" || task?.status === "pending";

  const { lastMessage } = useWebSocket(isRunning && task ? task.task_id : null);

  useEffect(() => {
    if (!lastMessage || !task) return;
    const updated = {
      ...task,
      status: (lastMessage.status ?? task.status) as TaskStatus["status"],
      progress_percent: lastMessage.progress_percent ?? task.progress_percent,
      message: (lastMessage.message as string) ?? task.message,
    };
    if (updated.status !== task.status || updated.progress_percent !== task.progress_percent) {
      setTask(updated);
      if (updated.status === "completed") {
        getPortfolioResult(task.task_id).then((res) => {
          if (res.success && res.data) setResult(res.data as PortfolioResult);
        });
      }
    }
  }, [lastMessage]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);
    setTask(null);
    const tickers = tickersInput.split(",").map((t) => t.trim().toUpperCase()).filter(Boolean);
    const res = await runPortfolio({
      tickers,
      start_date: startDate,
      end_date: endDate,
      initial_capital: capital,
      weighting_strategy: strategy,
    });
    setSubmitting(false);
    if (res.success && res.data) setTask(res.data);
  }

  const perf = result?.performance;

  const equityCurve = result?.snapshots.map((s) => ({
    time: s.date,
    value: s.total_value,
  })) ?? [];

  const lastSnapshot = result?.snapshots?.[result.snapshots.length - 1];
  const allocationData = lastSnapshot?.allocation
    ? Object.entries(lastSnapshot.allocation.weights).map(([name, value], i) => ({
        name,
        value: Math.round(value * 1000) / 10,
        fill: COLORS[i % COLORS.length],
      }))
    : [];

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Portfolio</h1>

      {/* Form */}
      <Card title="Portfolio Backtest konfigurieren">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>
                Ticker (kommagetrennt)
              </label>
              <input
                type="text"
                value={tickersInput}
                onChange={(e) => setTickersInput(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
                placeholder="NVDA, AAPL, MSFT"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>Strategie</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
              >
                <option value="equal">Equal Weight</option>
                <option value="risk_parity">Risk Parity</option>
                <option value="min_variance">Min Variance</option>
                <option value="signal_weighted">Signal Weighted</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              { label: "Startdatum", value: startDate, onChange: setStartDate, type: "date" },
              { label: "Enddatum", value: endDate, onChange: setEndDate, type: "date" },
              { label: "Startkapital", value: String(capital), onChange: (v: string) => setCapital(Number(v)), type: "number" },
            ].map((field) => (
              <div key={field.label}>
                <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>{field.label}</label>
                <input
                  type={field.type}
                  value={field.value}
                  onChange={(e) => field.onChange(e.target.value)}
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
                />
              </div>
            ))}
          </div>

          <button
            type="submit"
            disabled={submitting || isRunning}
            className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Wird gestartet..." : "Portfolio Backtest starten"}
          </button>
        </form>
      </Card>

      {/* Progress */}
      {task && isRunning && (
        <Card title="Fortschritt">
          <ProgressBar percent={task.progress_percent} label={task.message || "Portfolio Backtest läuft..."} />
        </Card>
      )}

      {submitting && (
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* Results */}
      {result && perf && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Gesamtrendite"
              value={formatPercent(perf.total_return ?? 0)}
              trend={(perf.total_return ?? 0) >= 0 ? "up" : "down"}
              mono
            />
            <MetricCard label="Sharpe Ratio" value={(perf.sharpe_ratio ?? 0).toFixed(2)} mono />
            <MetricCard label="Max Drawdown" value={formatPercent(perf.max_drawdown ?? 0)} trend="down" mono />
            <MetricCard label="Endwert" value={formatCurrency(perf.final_portfolio_value ?? capital)} mono />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Equity Curve (lightweight-charts) */}
            <Card title="Portfolio-Wert">
              <TradingChart equityCurve={equityCurve} mode="equity" height={280} />
            </Card>

            {/* Allocation Pie */}
            {allocationData.length > 0 && (
              <Card title="Allokation">
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={allocationData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ name, value }: { name: string; value: number }) => `${name}: ${value}%`}
                      >
                        {allocationData.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Legend />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--bg-card)",
                          border: "1px solid var(--border)",
                          borderRadius: "8px",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}
          </div>

          {/* Per-Ticker Performance */}
          {result.per_ticker_performance && (
            <Card title="Performance pro Ticker">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                      <th className="pb-2 font-medium">Ticker</th>
                      <th className="pb-2 font-medium">Rendite</th>
                      <th className="pb-2 font-medium">Sharpe</th>
                      <th className="pb-2 font-medium">Max DD</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(result.per_ticker_performance).map(([t, metrics]) => (
                      <tr key={t} className="border-b" style={{ borderColor: "var(--border)" }}>
                        <td className="py-2 font-medium" style={{ color: "var(--text-primary)" }}>{t}</td>
                        <td className={`py-2 font-mono ${(metrics.total_return ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {formatPercent(metrics.total_return ?? 0)}
                        </td>
                        <td className="py-2 font-mono" style={{ color: "var(--text-secondary)" }}>
                          {(metrics.sharpe_ratio ?? 0).toFixed(2)}
                        </td>
                        <td className="py-2 font-mono text-red-400">
                          {formatPercent(metrics.max_drawdown ?? 0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
