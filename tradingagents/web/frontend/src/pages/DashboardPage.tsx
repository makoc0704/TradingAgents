import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import MetricCard from "../components/common/MetricCard";
import StatusBadge from "../components/common/StatusBadge";
import Loading from "../components/common/Loading";
import { listTickers, getPipelineStatus } from "../api/client";
import type { PipelineStatus } from "../types";

export default function DashboardPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [tickerRes, pipelineRes] = await Promise.all([
        listTickers(),
        getPipelineStatus(),
      ]);
      if (tickerRes.success && tickerRes.data) setTickers(tickerRes.data);
      if (pipelineRes.success && pipelineRes.data)
        setPipeline(pipelineRes.data);
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <Loading message="Dashboard laden..." />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>

      {/* Quick Stats */}
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
          label="Status"
          value={pipeline?.running ? "Running" : "Stopped"}
          color={pipeline?.running ? "text-emerald-400" : "text-gray-400"}
        />
        <MetricCard
          label="System"
          value="Online"
          color="text-emerald-400"
          subtext="API erreichbar"
        />
      </div>

      {/* Recent Tickers */}
      <Card title="Analysierte Ticker">
        {tickers.length === 0 ? (
          <p className="text-gray-500">
            Noch keine Analyseergebnisse vorhanden. Starte eine Analyse ueber
            die Analyse-Seite.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tickers.map((t) => (
              <span
                key={t}
                className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-medium text-gray-200"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </Card>

      {/* Pipeline Jobs Overview */}
      {pipeline && pipeline.jobs.length > 0 && (
        <Card title="Pipeline Jobs">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left text-gray-500">
                  <th className="pb-3 font-medium">Job</th>
                  <th className="pb-3 font-medium">Typ</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Signal</th>
                  <th className="pb-3 font-medium">Letzter Lauf</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {pipeline.jobs.map((job) => (
                  <tr key={job.job_name}>
                    <td className="py-3 font-medium text-gray-200">
                      {job.job_name}
                    </td>
                    <td className="py-3 text-gray-400">{job.job_type}</td>
                    <td className="py-3">
                      <StatusBadge
                        label={job.last_status ?? "N/A"}
                        variant="status"
                      />
                    </td>
                    <td className="py-3">
                      {job.last_signal ? (
                        <StatusBadge
                          label={job.last_signal}
                          variant="signal"
                        />
                      ) : (
                        <span className="text-gray-600">--</span>
                      )}
                    </td>
                    <td className="py-3 text-gray-400">
                      {job.last_run_at ?? "--"}
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
          <a
            href="/analysis"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500"
          >
            Neue Analyse starten
          </a>
          <a
            href="/backtest"
            className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-600"
          >
            Backtest starten
          </a>
          <a
            href="/portfolio"
            className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-gray-200 transition-colors hover:bg-gray-600"
          >
            Portfolio Backtest
          </a>
        </div>
      </Card>
    </div>
  );
}
