import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Shield, Search } from "lucide-react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import { SkeletonCard } from "../components/common/Skeleton";
import EmptyState from "../components/common/EmptyState";
import { getRiskMetrics } from "../api/client";
import { formatPercent, formatNumber } from "../utils/format";
import type { RiskMetrics } from "../types";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

function normalizeForRadar(metrics: RiskMetrics) {
  return [
    { subject: "Sharpe", value: Math.min(Math.max(metrics.sharpe_ratio + 1, 0), 4) / 4 * 100 },
    { subject: "Sortino", value: Math.min(Math.max(metrics.sortino_ratio + 1, 0), 4) / 4 * 100 },
    { subject: "Volatilität", value: Math.max(0, 100 - metrics.annualized_volatility * 200) },
    { subject: "VaR95", value: Math.max(0, 100 + metrics.var_95 * 200) },
    { subject: "Max DD", value: Math.max(0, 100 + metrics.max_drawdown * 200) },
    { subject: "RSI", value: 100 - Math.abs(metrics.rsi - 50) * 2 },
  ];
}

export default function RiskPage() {
  const { ticker: paramTicker, date: paramDate } = useParams<{ ticker?: string; date?: string }>();
  const [ticker, setTicker] = useState(paramTicker ?? "NVDA");
  const [date, setDate] = useState(paramDate ?? "2024-06-05");
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadMetrics(t: string, d: string) {
    setLoading(true);
    setError(null);
    const res = await getRiskMetrics(t, d);
    if (res.success && res.data) {
      setMetrics(res.data);
    } else {
      setError(res.error ?? "Risikometriken konnten nicht geladen werden.");
      setMetrics(null);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (paramTicker && paramDate) {
      loadMetrics(paramTicker, paramDate);
    }
  }, [paramTicker, paramDate]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    loadMetrics(ticker.toUpperCase(), date);
  }

  const radarData = metrics ? normalizeForRadar(metrics) : [];

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        Risiko-Analyse
      </h1>

      {/* Search Form */}
      <Card title="Ticker auswählen">
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>Ticker</label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="w-32 rounded-lg border px-3 py-2 text-sm"
              style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
              placeholder="NVDA"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>Datum</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm"
              style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !ticker.trim()}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            Laden
          </button>
        </form>
      </Card>

      {loading && (
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && (
        <Card>
          <div className="text-sm text-red-400">{error}</div>
        </Card>
      )}

      {!loading && !metrics && !error && (
        <EmptyState
          icon={Shield}
          title="Keine Risikodaten"
          description="Wähle einen Ticker und ein Datum, um Risikometriken zu laden."
        />
      )}

      {metrics && (
        <>
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Sharpe Ratio"
              value={formatNumber(metrics.sharpe_ratio)}
              trend={metrics.sharpe_ratio >= 0 ? "up" : "down"}
              mono
            />
            <MetricCard
              label="Sortino Ratio"
              value={formatNumber(metrics.sortino_ratio)}
              trend={metrics.sortino_ratio >= 0 ? "up" : "down"}
              mono
            />
            <MetricCard
              label="VaR (95%)"
              value={formatPercent(metrics.var_95)}
              trend="down"
              mono
            />
            <MetricCard
              label="Max Drawdown"
              value={formatPercent(metrics.max_drawdown)}
              trend="down"
              mono
            />
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="Ann. Volatilität" value={formatPercent(metrics.annualized_volatility)} mono />
            <MetricCard label="ATR" value={`$${formatNumber(metrics.atr)}`} mono />
            <MetricCard label="Beta" value={formatNumber(metrics.beta)} mono />
            <MetricCard label="RSI" value={formatNumber(metrics.rsi, 0)} mono />
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="CVaR (95%)" value={formatPercent(metrics.cvar_95)} trend="down" mono />
            <MetricCard label="VaR (99%)" value={formatPercent(metrics.var_99)} trend="down" mono />
            <MetricCard label="SMA 50" value={`$${formatNumber(metrics.sma_50)}`} mono />
            <MetricCard label="SMA 200" value={`$${formatNumber(metrics.sma_200)}`} mono />
          </div>

          {/* Radar Chart */}
          <Card title="Risiko-Profil">
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar
                    name="Risiko-Score"
                    dataKey="value"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.2}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
