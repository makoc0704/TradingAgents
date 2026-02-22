import { useEffect, useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import StatusBadge from "../components/common/StatusBadge";
import Skeleton, { SkeletonCard } from "../components/common/Skeleton";
import EmptyState from "../components/common/EmptyState";
import TradingChart from "../components/charts/TradingChart";
import {
  getLivePortfolio,
  getLiveTrades,
  getLivePerformance,
  getLiveHistory,
  runLiveNow,
} from "../api/client";
import { formatCurrency, formatPercent, formatDateTime } from "../utils/format";
import type {
  LivePortfolio,
  LiveTrade,
  LivePerformance,
  LiveRunSnapshot,
  TaskStatus,
} from "../types";

export default function LiveTradingPage() {
  const [portfolio, setPortfolio] = useState<LivePortfolio | null>(null);
  const [trades, setTrades] = useState<LiveTrade[]>([]);
  const [performance, setPerformance] = useState<LivePerformance | null>(null);
  const [history, setHistory] = useState<LiveRunSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [runTask, setRunTask] = useState<TaskStatus | null>(null);

  async function loadAll() {
    setLoading(true);
    const [pRes, tRes, perfRes, hRes] = await Promise.all([
      getLivePortfolio(),
      getLiveTrades(),
      getLivePerformance(),
      getLiveHistory(),
    ]);
    if (pRes.success && pRes.data) setPortfolio(pRes.data);
    if (tRes.success && tRes.data) setTrades(tRes.data);
    if (perfRes.success && perfRes.data) setPerformance(perfRes.data);
    if (hRes.success && hRes.data) setHistory(hRes.data);
    setLoading(false);
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleRunNow() {
    setRunning(true);
    const res = await runLiveNow();
    if (res.success && res.data) setRunTask(res.data);
    setRunning(false);
    setTimeout(loadAll, 3000);
  }

  const equityCurve = history.map((s) => ({ time: s.date, value: s.portfolio_value }));

  const tradeMarkers = trades
    .filter((t) => t.action !== "HOLD")
    .map((t) => ({
      time: t.date,
      position: (t.action === "BUY" ? "belowBar" : "aboveBar") as "belowBar" | "aboveBar",
      color: t.action === "BUY" ? "#34d399" : "#f87171",
      shape: (t.action === "BUY" ? "arrowUp" : "arrowDown") as "arrowUp" | "arrowDown",
      text: `${t.action} ${t.shares}`,
    }));

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton height="h-8" className="w-1/4" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonCard />
      </div>
    );
  }

  const noData = !portfolio && trades.length === 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Live Trading</h1>
        <div className="flex gap-2">
          <button
            onClick={loadAll}
            className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors hover:border-[var(--border-hover)]"
            style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Aktualisieren
          </button>
          <button
            onClick={handleRunNow}
            disabled={running}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            {running ? "Läuft..." : "Jetzt ausführen"}
          </button>
        </div>
      </div>

      {runTask && (
        <Card>
          <div className="flex items-center gap-3 text-sm">
            <StatusBadge label={runTask.status} />
            <span className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>{runTask.task_id}</span>
          </div>
        </Card>
      )}

      {noData ? (
        <EmptyState
          icon={Play}
          title="Kein Live-Portfolio"
          description="Starte einen Live-Trading-Lauf, um Daten zu sammeln."
        />
      ) : (
        <>
          {/* Portfolio Hero */}
          {portfolio && (
            <Card gradient>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                    Portfolio-Wert
                  </div>
                  <div className="mt-1 text-3xl font-bold font-mono" style={{ color: "var(--text-primary)" }}>
                    {formatCurrency(portfolio.total_value)}
                  </div>
                  <div className="mt-1 flex items-center gap-3">
                    <span className={`text-sm font-medium ${portfolio.total_return >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {formatPercent(portfolio.total_return)} gesamt
                    </span>
                    <span className={`text-sm ${portfolio.daily_return >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {formatPercent(portfolio.daily_return)} heute
                    </span>
                  </div>
                </div>
                <div className="text-right text-sm" style={{ color: "var(--text-muted)" }}>
                  Cash: {formatCurrency(portfolio.cash)}
                  <br />
                  Positionen: {portfolio.positions.length}
                </div>
              </div>
            </Card>
          )}

          {/* KPI Row */}
          {performance && (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <MetricCard
                label="Annualisierte Rendite"
                value={formatPercent(performance.annualized_return)}
                trend={performance.annualized_return >= 0 ? "up" : "down"}
                mono
              />
              <MetricCard label="Sharpe Ratio" value={performance.sharpe_ratio.toFixed(2)} mono />
              <MetricCard label="Max Drawdown" value={formatPercent(performance.max_drawdown)} trend="down" mono />
              <MetricCard label="Win Rate" value={formatPercent(performance.win_rate)} mono />
            </div>
          )}

          {/* Equity Curve */}
          {equityCurve.length > 1 && (
            <Card title="Equity-Kurve">
              <TradingChart equityCurve={equityCurve} markers={tradeMarkers} mode="equity" height={350} />
            </Card>
          )}

          {/* Positions Table */}
          {portfolio && portfolio.positions.length > 0 && (
            <Card title="Offene Positionen">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                      <th className="pb-3 font-medium">Ticker</th>
                      <th className="pb-3 font-medium">Stück</th>
                      <th className="pb-3 font-medium">Einstieg</th>
                      <th className="pb-3 font-medium">Aktuell</th>
                      <th className="pb-3 font-medium">P&L</th>
                      <th className="pb-3 font-medium">Gewicht</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.positions.map((pos) => (
                      <tr key={pos.ticker} className="border-b" style={{ borderColor: "var(--border)" }}>
                        <td className="py-3 font-medium" style={{ color: "var(--text-primary)" }}>{pos.ticker}</td>
                        <td className="py-3 font-mono" style={{ color: "var(--text-secondary)" }}>{pos.shares}</td>
                        <td className="py-3 font-mono" style={{ color: "var(--text-secondary)" }}>${pos.avg_entry_price.toFixed(2)}</td>
                        <td className="py-3 font-mono" style={{ color: "var(--text-secondary)" }}>${pos.current_price.toFixed(2)}</td>
                        <td className={`py-3 font-mono ${pos.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {formatCurrency(pos.unrealized_pnl)} ({formatPercent(pos.unrealized_pnl_pct)})
                        </td>
                        <td className="py-3 font-mono" style={{ color: "var(--text-secondary)" }}>
                          {formatPercent(pos.weight)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Trade Log */}
          {trades.length > 0 && (
            <Card title="Trade-Log">
              <div className="max-h-80 overflow-y-auto">
                <div className="space-y-2">
                  {trades.filter((t) => t.action !== "HOLD").map((t, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 rounded-lg border p-3"
                      style={{ background: "var(--bg-primary)", borderColor: "var(--border)" }}
                    >
                      <StatusBadge label={t.action} variant="signal" />
                      <span className="font-medium" style={{ color: "var(--text-primary)" }}>{t.ticker}</span>
                      <span className="font-mono text-sm" style={{ color: "var(--text-secondary)" }}>
                        {t.shares} @ ${t.price.toFixed(2)}
                      </span>
                      <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
                        {formatDateTime(t.date)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
