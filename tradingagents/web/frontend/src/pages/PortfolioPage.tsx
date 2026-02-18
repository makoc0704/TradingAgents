import { useState } from "react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import Loading from "../components/common/Loading";
import ProgressBar from "../components/common/ProgressBar";
import { runPortfolio, getPortfolioStatus, getPortfolioResult } from "../api/client";
import { useInterval } from "../hooks/useInterval";
import { formatPercent, formatCurrency } from "../utils/format";
import type { TaskStatus, PortfolioResult } from "../types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
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

  useInterval(
    async () => {
      if (!task) return;
      const statusRes = await getPortfolioStatus(task.task_id);
      if (statusRes.success && statusRes.data) {
        setTask(statusRes.data);
        if (statusRes.data.status === "completed") {
          const resultRes = await getPortfolioResult(task.task_id);
          if (resultRes.success && resultRes.data) {
            setResult(resultRes.data as PortfolioResult);
          }
        }
      }
    },
    isRunning ? 3000 : null
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setResult(null);
    setTask(null);

    const tickers = tickersInput
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);

    const res = await runPortfolio({
      tickers,
      start_date: startDate,
      end_date: endDate,
      initial_capital: capital,
      weighting_strategy: strategy,
    });

    setSubmitting(false);
    if (res.success && res.data) {
      setTask(res.data);
    }
  }

  const perf = result?.performance;

  const lastSnapshot = result?.snapshots?.[result.snapshots.length - 1];
  const allocationData = lastSnapshot?.allocation
    ? Object.entries(lastSnapshot.allocation.weights).map(([name, value], i) => ({
        name,
        value: Math.round(value * 1000) / 10,
        fill: COLORS[i % COLORS.length],
      }))
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Portfolio</h1>

      {/* Config Form */}
      <Card title="Portfolio Backtest konfigurieren">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Ticker (kommagetrennt)
              </label>
              <input
                type="text"
                value={tickersInput}
                onChange={(e) => setTickersInput(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
                placeholder="NVDA, AAPL, MSFT"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Strategie
              </label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="equal">Equal Weight</option>
                <option value="risk_parity">Risk Parity</option>
                <option value="min_variance">Min Variance</option>
                <option value="signal_weighted">Signal Weighted</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Startdatum
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Enddatum
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Startkapital
              </label>
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              />
            </div>
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
          <ProgressBar
            percent={task.progress_percent}
            label={task.message || "Portfolio Backtest laeuft..."}
          />
        </Card>
      )}

      {submitting && <Loading message="Portfolio Backtest wird gestartet..." />}

      {/* Results */}
      {result && perf && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Gesamtrendite"
              value={formatPercent(perf.total_return ?? 0)}
              color={
                (perf.total_return ?? 0) >= 0
                  ? "text-emerald-400"
                  : "text-red-400"
              }
            />
            <MetricCard
              label="Sharpe Ratio"
              value={String((perf.sharpe_ratio ?? 0).toFixed(2))}
            />
            <MetricCard
              label="Max Drawdown"
              value={formatPercent(perf.max_drawdown ?? 0)}
              color="text-red-400"
            />
            <MetricCard
              label="Endwert"
              value={formatCurrency(perf.final_portfolio_value ?? capital)}
            />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Portfolio Value Chart */}
            <Card title="Portfolio-Wert">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.snapshots}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#9ca3af", fontSize: 11 }}
                      stroke="#374151"
                    />
                    <YAxis
                      tick={{ fill: "#9ca3af", fontSize: 11 }}
                      stroke="#374151"
                      tickFormatter={(v: number) =>
                        `$${(v / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#111827",
                        border: "1px solid #374151",
                        borderRadius: "8px",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="total_value"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Allocation Pie */}
            {allocationData.length > 0 && (
              <Card title="Allokation">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={allocationData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ name, value }: { name: string; value: number }) =>
                          `${name}: ${value}%`
                        }
                      >
                        {allocationData.map((entry, i) => (
                          <Cell key={i} fill={entry.fill} />
                        ))}
                      </Pie>
                      <Legend />
                      <Tooltip />
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
                    <tr className="border-b border-gray-800 text-left text-gray-500">
                      <th className="pb-2 font-medium">Ticker</th>
                      <th className="pb-2 font-medium">Rendite</th>
                      <th className="pb-2 font-medium">Sharpe</th>
                      <th className="pb-2 font-medium">Max DD</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {Object.entries(result.per_ticker_performance).map(
                      ([ticker, metrics]) => (
                        <tr key={ticker}>
                          <td className="py-2 font-medium text-gray-200">
                            {ticker}
                          </td>
                          <td
                            className={`py-2 ${
                              (metrics.total_return ?? 0) >= 0
                                ? "text-emerald-400"
                                : "text-red-400"
                            }`}
                          >
                            {formatPercent(metrics.total_return ?? 0)}
                          </td>
                          <td className="py-2 text-gray-300">
                            {(metrics.sharpe_ratio ?? 0).toFixed(2)}
                          </td>
                          <td className="py-2 text-red-400">
                            {formatPercent(metrics.max_drawdown ?? 0)}
                          </td>
                        </tr>
                      )
                    )}
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
