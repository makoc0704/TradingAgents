import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  Search,
  TrendingUp,
  Briefcase,
  ExternalLink,
} from "lucide-react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import StatusBadge from "../components/common/StatusBadge";
import EmptyState from "../components/common/EmptyState";
import Skeleton, { SkeletonCard } from "../components/common/Skeleton";
import SparkLine from "../components/charts/SparkLine";
import {
  listTickers,
  getPipelineStatus,
  getLivePortfolio,
  getLiveHistory,
} from "../api/client";
import { formatCurrency, formatPercent } from "../utils/format";
import type { PipelineStatus, LivePortfolio, LiveRunSnapshot } from "../types";

export default function DashboardPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [portfolio, setPortfolio] = useState<LivePortfolio | null>(null);
  const [equityHistory, setEquityHistory] = useState<LiveRunSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [tickerRes, pipelineRes, portfolioRes, historyRes] = await Promise.all([
        listTickers(),
        getPipelineStatus(),
        getLivePortfolio(),
        getLiveHistory(),
      ]);
      if (tickerRes.success && tickerRes.data) setTickers(tickerRes.data);
      if (pipelineRes.success && pipelineRes.data) setPipeline(pipelineRes.data);
      if (portfolioRes.success && portfolioRes.data) setPortfolio(portfolioRes.data);
      if (historyRes.success && historyRes.data) setEquityHistory(historyRes.data);
      setLoading(false);
    }
    load();
  }, []);

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

  const sparkData = equityHistory.map((s) => ({ time: s.date, value: s.portfolio_value }));

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Dashboard</h1>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Analysierte Ticker"
          value={String(tickers.length)}
          subtext="mit gespeicherten Ergebnissen"
        />
        <MetricCard
          label="Pipeline Jobs"
          value={String(pipeline?.total_jobs ?? 0)}
          subtext={`${pipeline?.enabled_jobs ?? 0} aktiv`}
        />
        <MetricCard
          label="Pipeline"
          value={pipeline?.running ? "Running" : "Stopped"}
          trend={pipeline?.running ? "up" : "neutral"}
        />
        <MetricCard
          label="System"
          value="Online"
          trend="up"
          subtext="API erreichbar"
        />
      </div>

      {/* Live Portfolio Hero */}
      {portfolio && (
        <Card gradient>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                Live Portfolio
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
            {sparkData.length > 1 && (
              <SparkLine
                data={sparkData}
                color={portfolio.total_return >= 0 ? "#34d399" : "#f87171"}
                width={160}
                height={50}
              />
            )}
          </div>
          <div className="mt-4">
            <Link
              to="/live"
              className="inline-flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Zum Live Trading
            </Link>
          </div>
        </Card>
      )}

      {/* Analysed Tickers */}
      <Card title="Analysierte Ticker">
        {tickers.length === 0 ? (
          <EmptyState
            icon={Search}
            title="Noch keine Analysen"
            description="Starte eine Analyse, um Ticker-Ergebnisse zu sehen."
          />
        ) : (
          <div className="flex flex-wrap gap-2">
            {tickers.map((t) => (
              <Link
                key={t}
                to={`/history`}
                className="rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors hover:border-[var(--border-hover)]"
                style={{
                  background: "var(--bg-primary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              >
                {t}
              </Link>
            ))}
          </div>
        )}
      </Card>

      {/* Pipeline Jobs */}
      {pipeline && pipeline.jobs.length > 0 && (
        <Card title="Pipeline Jobs">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                  <th className="pb-3 font-medium">Job</th>
                  <th className="pb-3 font-medium">Typ</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Signal</th>
                  <th className="pb-3 font-medium">Letzter Lauf</th>
                </tr>
              </thead>
              <tbody>
                {pipeline.jobs.map((job) => (
                  <tr key={job.job_name} className="border-b" style={{ borderColor: "var(--border)" }}>
                    <td className="py-3 font-medium" style={{ color: "var(--text-primary)" }}>
                      {job.job_name}
                    </td>
                    <td className="py-3" style={{ color: "var(--text-secondary)" }}>{job.job_type}</td>
                    <td className="py-3">
                      <StatusBadge label={job.last_status ?? "N/A"} variant="status" />
                    </td>
                    <td className="py-3">
                      {job.last_signal ? (
                        <StatusBadge label={job.last_signal} variant="signal" />
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>–</span>
                      )}
                    </td>
                    <td className="py-3" style={{ color: "var(--text-secondary)" }}>
                      {job.last_run_at ?? "–"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <Card title="Schnellaktionen">
        <div className="flex flex-wrap gap-3">
          <Link
            to="/analysis"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500"
          >
            <Search className="h-4 w-4" />
            Neue Analyse
          </Link>
          <Link
            to="/live"
            className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            style={{ background: "var(--bg-card-hover)", color: "var(--text-primary)" }}
          >
            <Activity className="h-4 w-4" />
            Live Trading
          </Link>
          <Link
            to="/backtest"
            className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            style={{ background: "var(--bg-card-hover)", color: "var(--text-primary)" }}
          >
            <TrendingUp className="h-4 w-4" />
            Backtest
          </Link>
          <Link
            to="/portfolio"
            className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            style={{ background: "var(--bg-card-hover)", color: "var(--text-primary)" }}
          >
            <Briefcase className="h-4 w-4" />
            Portfolio
          </Link>
        </div>
      </Card>
    </div>
  );
}
