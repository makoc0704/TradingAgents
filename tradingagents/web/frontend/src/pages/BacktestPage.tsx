import { useState } from "react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import Loading from "../components/common/Loading";
import ProgressBar from "../components/common/ProgressBar";
import StatusBadge from "../components/common/StatusBadge";
import { runBacktest, getBacktestStatus, getBacktestResult } from "../api/client";
import { useInterval } from "../hooks/useInterval";
import { formatPercent, formatCurrency } from "../utils/format";
import type { TaskStatus, BacktestResult } from "../types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function BacktestPage() {
  const [ticker, setTicker] = useState("NVDA");
  const [startDate, setStartDate] = useState("2024-06-03");
  const [endDate, setEndDate] = useState("2024-06-07");
  const [profile, setProfile] = useState("quick");
  const [capital, setCapital] = useState(100000);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRunning =
    task?.status === "running" || task?.status === "pending";

  useInterval(
    async () => {
      if (!task) return;
      const statusRes = await getBacktestStatus(task.task_id);
      if (statusRes.success && statusRes.data) {
        setTask(statusRes.data);
        if (statusRes.data.status === "completed") {
          const resultRes = await getBacktestResult(task.task_id);
          if (resultRes.success && resultRes.data) {
            setResult(resultRes.data as BacktestResult);
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

    const res = await runBacktest({
      ticker: ticker.toUpperCase(),
      start_date: startDate,
      end_date: endDate,
      initial_capital: capital,
      backtest_profile: profile,
    });

    setSubmitting(false);
    if (res.success && res.data) {
      setTask(res.data);
    }
  }

  const perf = result?.performance;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Backtest</h1>

      {/* Config Form */}
      <Card title="Backtest konfigurieren">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Ticker
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              />
            </div>
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

          <div>
            <label className="mb-2 block text-sm text-gray-400">Profil</label>
            <div className="flex gap-2">
              {["quick", "standard", "full"].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setProfile(p)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                    profile === p
                      ? "border-blue-500 bg-blue-600/20 text-blue-400"
                      : "border-gray-700 text-gray-500 hover:border-gray-600"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || isRunning}
            className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Wird gestartet..." : "Backtest starten"}
          </button>
        </form>
      </Card>

      {/* Progress */}
      {task && isRunning && (
        <Card title="Fortschritt">
          <ProgressBar
            percent={task.progress_percent}
            label={task.message || "Backtest laeuft..."}
          />
        </Card>
      )}

      {task && task.status === "failed" && (
        <Card>
          <div className="text-red-400">
            Backtest fehlgeschlagen. Bitte Konfiguration pruefen.
          </div>
        </Card>
      )}

      {submitting && <Loading message="Backtest wird gestartet..." />}

      {/* Results */}
      {result && perf && (
        <>
          {/* Performance KPIs */}
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

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Win Rate"
              value={formatPercent(perf.win_rate ?? 0)}
            />
            <MetricCard
              label="Trades"
              value={String(result.total_trades)}
            />
            <MetricCard
              label="Buy & Hold"
              value={formatPercent(perf.buy_and_hold_return ?? 0)}
            />
            <MetricCard
              label="Alpha"
              value={formatPercent(perf.alpha ?? 0)}
              color={
                (perf.alpha ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"
              }
            />
          </div>

          {/* Equity Curve */}
          <Card title="Equity-Kurve">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={result.daily_snapshots}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#9ca3af", fontSize: 12 }}
                    stroke="#374151"
                  />
                  <YAxis
                    tick={{ fill: "#9ca3af", fontSize: 12 }}
                    stroke="#374151"
                    tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#111827",
                      border: "1px solid #374151",
                      borderRadius: "8px",
                    }}
                    labelStyle={{ color: "#9ca3af" }}
                    formatter={(v: number) => [
                      `$${v.toLocaleString()}`,
                      "Portfolio",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="portfolio_value"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Trade History */}
          <Card title="Trade-Historie">
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-900">
                  <tr className="border-b border-gray-800 text-left text-gray-500">
                    <th className="pb-2 font-medium">Datum</th>
                    <th className="pb-2 font-medium">Aktion</th>
                    <th className="pb-2 font-medium">Preis</th>
                    <th className="pb-2 font-medium">Stueck</th>
                    <th className="pb-2 font-medium">Portfolio</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {result.trades
                    .filter((t) => t.action !== "HOLD")
                    .map((t, i) => (
                      <tr key={i}>
                        <td className="py-2 text-gray-300">{t.date}</td>
                        <td className="py-2">
                          <StatusBadge label={t.action} variant="signal" />
                        </td>
                        <td className="py-2 text-gray-300">
                          ${t.price.toFixed(2)}
                        </td>
                        <td className="py-2 text-gray-300">{t.shares}</td>
                        <td className="py-2 text-gray-300">
                          {formatCurrency(t.portfolio_value)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
