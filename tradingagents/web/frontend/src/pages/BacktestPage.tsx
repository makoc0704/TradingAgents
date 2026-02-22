import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import ProgressBar from "../components/common/ProgressBar";
import StatusBadge from "../components/common/StatusBadge";
import { SkeletonCard } from "../components/common/Skeleton";
import TradingChart from "../components/charts/TradingChart";
import { runBacktest, getBacktestResult } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import { formatPercent, formatCurrency } from "../utils/format";
import type { TaskStatus, BacktestResult } from "../types";

export default function BacktestPage() {
  const [ticker, setTicker] = useState("NVDA");
  const [startDate, setStartDate] = useState("2024-06-03");
  const [endDate, setEndDate] = useState("2024-06-07");
  const [profile, setProfile] = useState("quick");
  const [capital, setCapital] = useState(100000);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<BacktestResult | null>(null);
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
        getBacktestResult(task.task_id).then((res) => {
          if (res.success && res.data) setResult(res.data as BacktestResult);
        });
      }
    }
  }, [lastMessage]);

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
    if (res.success && res.data) setTask(res.data);
  }

  const perf = result?.performance;

  const equityCurve = result?.daily_snapshots.map((s) => ({
    time: s.date,
    value: s.portfolio_value,
  })) ?? [];

  const tradeMarkers = result?.trades
    .filter((t) => t.action !== "HOLD")
    .map((t) => ({
      time: t.date,
      position: (t.action === "BUY" ? "belowBar" : "aboveBar") as "belowBar" | "aboveBar",
      color: t.action === "BUY" ? "#34d399" : "#f87171",
      shape: (t.action === "BUY" ? "arrowUp" : "arrowDown") as "arrowUp" | "arrowDown",
      text: `${t.action} ${t.shares}`,
    })) ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Backtest</h1>

      {/* Form */}
      <Card title="Backtest konfigurieren">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Ticker", value: ticker, onChange: (v: string) => setTicker(v), type: "text" },
              { label: "Startdatum", value: startDate, onChange: (v: string) => setStartDate(v), type: "date" },
              { label: "Enddatum", value: endDate, onChange: (v: string) => setEndDate(v), type: "date" },
              { label: "Startkapital", value: String(capital), onChange: (v: string) => setCapital(Number(v)), type: "number" },
            ].map((field) => (
              <div key={field.label}>
                <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>
                  {field.label}
                </label>
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

          <div>
            <label className="mb-2 block text-sm" style={{ color: "var(--text-secondary)" }}>Profil</label>
            <div className="flex gap-2">
              {["quick", "standard", "full"].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setProfile(p)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                    profile === p
                      ? "border-blue-500 bg-blue-600/20 text-blue-400"
                      : "hover:border-[var(--border-hover)]"
                  }`}
                  style={profile !== p ? { borderColor: "var(--border)", color: "var(--text-muted)" } : undefined}
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
          <ProgressBar percent={task.progress_percent} label={task.message || "Backtest läuft..."} />
        </Card>
      )}

      {task?.status === "failed" && (
        <Card>
          <div className="text-sm text-red-400">Backtest fehlgeschlagen. Bitte Konfiguration prüfen.</div>
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

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="Win Rate" value={formatPercent(perf.win_rate ?? 0)} mono />
            <MetricCard label="Trades" value={String(result.total_trades)} />
            <MetricCard label="Buy & Hold" value={formatPercent(perf.buy_and_hold_return ?? 0)} mono />
            <MetricCard
              label="Alpha"
              value={formatPercent(perf.alpha ?? 0)}
              trend={(perf.alpha ?? 0) >= 0 ? "up" : "down"}
              mono
            />
          </div>

          {/* Equity Curve (lightweight-charts) */}
          <Card title="Equity-Kurve">
            <TradingChart equityCurve={equityCurve} markers={tradeMarkers} mode="equity" height={380} />
          </Card>

          {/* Trade History */}
          <Card title="Trade-Historie">
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0" style={{ background: "var(--bg-card)" }}>
                  <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                    <th className="pb-2 font-medium">Datum</th>
                    <th className="pb-2 font-medium">Aktion</th>
                    <th className="pb-2 font-medium">Preis</th>
                    <th className="pb-2 font-medium">Stück</th>
                    <th className="pb-2 font-medium">Portfolio</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades
                    .filter((t) => t.action !== "HOLD")
                    .map((t, i) => (
                      <tr key={i} className="border-b" style={{ borderColor: "var(--border)" }}>
                        <td className="py-2" style={{ color: "var(--text-secondary)" }}>{t.date}</td>
                        <td className="py-2"><StatusBadge label={t.action} variant="signal" /></td>
                        <td className="py-2 font-mono" style={{ color: "var(--text-secondary)" }}>${t.price.toFixed(2)}</td>
                        <td className="py-2 font-mono" style={{ color: "var(--text-secondary)" }}>{t.shares}</td>
                        <td className="py-2 font-mono" style={{ color: "var(--text-secondary)" }}>{formatCurrency(t.portfolio_value)}</td>
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
