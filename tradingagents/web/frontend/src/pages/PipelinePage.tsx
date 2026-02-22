import { useEffect, useState } from "react";
import { Settings, RefreshCw, Play, Clock } from "lucide-react";
import Card from "../components/common/Card";
import StatusBadge from "../components/common/StatusBadge";
import Skeleton, { SkeletonCard } from "../components/common/Skeleton";
import EmptyState from "../components/common/EmptyState";
import { getPipelineStatus, getJobHistory, runPipelineJob } from "../api/client";
import { formatDateTime } from "../utils/format";
import type { PipelineStatus } from "../types";

export default function PipelinePage() {
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [runningJob, setRunningJob] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  async function loadStatus() {
    setLoading(true);
    const res = await getPipelineStatus();
    if (res.success && res.data) setPipeline(res.data);
    setLoading(false);
  }

  async function loadHistory(jobName: string) {
    setSelectedJob(jobName);
    setHistoryLoading(true);
    const res = await getJobHistory(jobName);
    if (res.success && res.data) setHistory(res.data as Record<string, unknown>[]);
    setHistoryLoading(false);
  }

  async function handleRunNow(jobName: string) {
    setRunningJob(jobName);
    await runPipelineJob(jobName);
    setRunningJob(null);
    loadStatus();
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton height="h-8" className="w-1/4" />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Pipeline</h1>
        <button
          onClick={loadStatus}
          className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition-colors hover:border-[var(--border-hover)]"
          style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Aktualisieren
        </button>
      </div>

      {/* Status */}
      <Card>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Status:</span>
            <span className={pipeline?.running ? "text-emerald-400" : ""} style={!pipeline?.running ? { color: "var(--text-secondary)" } : undefined}>
              {pipeline?.running ? "Running" : "Stopped"}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Jobs:</span>
            <span style={{ color: "var(--text-primary)" }}>{pipeline?.total_jobs ?? 0}</span>
          </div>
        </div>
      </Card>

      {/* Jobs */}
      {pipeline && pipeline.jobs.length > 0 ? (
        <Card title="Jobs">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                  <th className="pb-3 font-medium">Job</th>
                  <th className="pb-3 font-medium">Typ</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Signal</th>
                  <th className="pb-3 font-medium">Letzter Lauf</th>
                  <th className="pb-3 font-medium">Dauer</th>
                  <th className="pb-3 font-medium">Aktionen</th>
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
                      {job.last_run_at ? formatDateTime(job.last_run_at) : "–"}
                    </td>
                    <td className="py-3" style={{ color: "var(--text-secondary)" }}>
                      {job.last_duration_seconds ? `${job.last_duration_seconds.toFixed(1)}s` : "–"}
                    </td>
                    <td className="py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => loadHistory(job.job_name)}
                          className="flex items-center gap-1 rounded border px-2 py-1 text-xs transition-colors hover:border-[var(--border-hover)]"
                          style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}
                        >
                          <Clock className="h-3 w-3" />
                          Historie
                        </button>
                        <button
                          onClick={() => handleRunNow(job.job_name)}
                          disabled={runningJob === job.job_name}
                          className="flex items-center gap-1 rounded border border-blue-700 px-2 py-1 text-xs text-blue-400 hover:bg-blue-600/20 disabled:opacity-50"
                        >
                          <Play className="h-3 w-3" />
                          {runningJob === job.job_name ? "Läuft..." : "Ausführen"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={Settings}
          title="Keine Pipeline-Jobs"
          description="Erstelle eine pipeline.yaml und starte die Pipeline."
        />
      )}

      {/* Job History */}
      {selectedJob && (
        <Card title={`Historie: ${selectedJob}`}>
          {historyLoading ? (
            <Skeleton lines={5} />
          ) : history.length === 0 ? (
            <div className="text-sm" style={{ color: "var(--text-muted)" }}>Keine Einträge vorhanden.</div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0" style={{ background: "var(--bg-card)" }}>
                  <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                    <th className="pb-2 font-medium">Zeitpunkt</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Signal</th>
                    <th className="pb-2 font-medium">Dauer</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((entry, i) => (
                    <tr key={i} className="border-b" style={{ borderColor: "var(--border)" }}>
                      <td className="py-2" style={{ color: "var(--text-secondary)" }}>
                        {formatDateTime((entry as Record<string, string>).finished_at ?? "")}
                      </td>
                      <td className="py-2">
                        <StatusBadge label={(entry as Record<string, string>).status ?? "N/A"} />
                      </td>
                      <td className="py-2">
                        {(entry as Record<string, string>).signal ? (
                          <StatusBadge label={(entry as Record<string, string>).signal ?? ""} variant="signal" />
                        ) : "–"}
                      </td>
                      <td className="py-2" style={{ color: "var(--text-secondary)" }}>
                        {(entry as Record<string, number>).duration_seconds
                          ? `${(entry as Record<string, number>).duration_seconds.toFixed(1)}s`
                          : "–"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
