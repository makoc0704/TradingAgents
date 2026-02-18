import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import StatusBadge from "../components/common/StatusBadge";
import Loading from "../components/common/Loading";
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

  if (loading) return <Loading message="Pipeline-Status laden..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Pipeline</h1>
        <button
          onClick={loadStatus}
          className="rounded-lg border border-gray-700 px-3 py-1.5 text-sm text-gray-400 transition-colors hover:border-gray-600 hover:text-gray-200"
        >
          Aktualisieren
        </button>
      </div>

      {/* Status Overview */}
      <Card>
        <div className="flex items-center gap-6">
          <div>
            <span className="text-sm text-gray-500">Status:</span>{" "}
            <span
              className={
                pipeline?.running ? "text-emerald-400" : "text-gray-400"
              }
            >
              {pipeline?.running ? "Running" : "Stopped"}
            </span>
          </div>
          <div>
            <span className="text-sm text-gray-500">Jobs:</span>{" "}
            <span className="text-gray-200">{pipeline?.total_jobs ?? 0}</span>
          </div>
        </div>
      </Card>

      {/* Jobs List */}
      {pipeline && pipeline.jobs.length > 0 ? (
        <Card title="Jobs">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-left text-gray-500">
                  <th className="pb-3 font-medium">Job</th>
                  <th className="pb-3 font-medium">Typ</th>
                  <th className="pb-3 font-medium">Letzter Status</th>
                  <th className="pb-3 font-medium">Signal</th>
                  <th className="pb-3 font-medium">Letzter Lauf</th>
                  <th className="pb-3 font-medium">Dauer</th>
                  <th className="pb-3 font-medium">Aktionen</th>
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
                        <StatusBadge label={job.last_signal} variant="signal" />
                      ) : (
                        <span className="text-gray-600">--</span>
                      )}
                    </td>
                    <td className="py-3 text-gray-400">
                      {job.last_run_at
                        ? formatDateTime(job.last_run_at)
                        : "--"}
                    </td>
                    <td className="py-3 text-gray-400">
                      {job.last_duration_seconds
                        ? `${job.last_duration_seconds.toFixed(1)}s`
                        : "--"}
                    </td>
                    <td className="py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => loadHistory(job.job_name)}
                          className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-400 hover:border-gray-500 hover:text-gray-200"
                        >
                          Historie
                        </button>
                        <button
                          onClick={() => handleRunNow(job.job_name)}
                          disabled={runningJob === job.job_name}
                          className="rounded border border-blue-700 px-2 py-1 text-xs text-blue-400 hover:bg-blue-600/20 disabled:opacity-50"
                        >
                          {runningJob === job.job_name
                            ? "Laeuft..."
                            : "Jetzt ausfuehren"}
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
        <Card>
          <p className="text-gray-500">
            Keine Pipeline-Jobs konfiguriert. Erstelle eine{" "}
            <code className="text-gray-400">pipeline.yaml</code> und starte die
            Pipeline.
          </p>
        </Card>
      )}

      {/* Job History */}
      {selectedJob && (
        <Card title={`Historie: ${selectedJob}`}>
          {historyLoading ? (
            <Loading message="Historie laden..." />
          ) : history.length === 0 ? (
            <p className="text-gray-500">Keine Eintraege vorhanden.</p>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-900">
                  <tr className="border-b border-gray-800 text-left text-gray-500">
                    <th className="pb-2 font-medium">Zeitpunkt</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Signal</th>
                    <th className="pb-2 font-medium">Dauer</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50">
                  {history.map((entry, i) => (
                    <tr key={i}>
                      <td className="py-2 text-gray-300">
                        {formatDateTime(
                          (entry as Record<string, string>).finished_at ?? ""
                        )}
                      </td>
                      <td className="py-2">
                        <StatusBadge
                          label={
                            (entry as Record<string, string>).status ?? "N/A"
                          }
                        />
                      </td>
                      <td className="py-2">
                        {(entry as Record<string, string>).signal ? (
                          <StatusBadge
                            label={
                              (entry as Record<string, string>).signal ?? ""
                            }
                            variant="signal"
                          />
                        ) : (
                          "--"
                        )}
                      </td>
                      <td className="py-2 text-gray-400">
                        {(entry as Record<string, number>).duration_seconds
                          ? `${(entry as Record<string, number>).duration_seconds.toFixed(1)}s`
                          : "--"}
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
