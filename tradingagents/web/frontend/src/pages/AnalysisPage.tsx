import { useState } from "react";
import Card from "../components/common/Card";
import Loading from "../components/common/Loading";
import StatusBadge from "../components/common/StatusBadge";
import ProgressBar from "../components/common/ProgressBar";
import { runAnalysis, getAnalysisStatus } from "../api/client";
import { useInterval } from "../hooks/useInterval";
import type { TaskStatus } from "../types";

export default function AnalysisPage() {
  const [ticker, setTicker] = useState("NVDA");
  const [date, setDate] = useState("2024-06-05");
  const [analysts, setAnalysts] = useState(["market", "fundamentals"]);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRunning =
    task?.status === "running" || task?.status === "pending";

  useInterval(
    async () => {
      if (!task) return;
      const res = await getAnalysisStatus(task.task_id);
      if (res.success && res.data) setTask(res.data);
    },
    isRunning ? 3000 : null
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setTask(null);

    const res = await runAnalysis({
      ticker: ticker.toUpperCase(),
      analysis_date: date,
      selected_analysts: analysts,
    });

    setSubmitting(false);
    if (res.success && res.data) {
      setTask(res.data);
    }
  }

  function toggleAnalyst(name: string) {
    setAnalysts((prev) =>
      prev.includes(name) ? prev.filter((a) => a !== name) : [...prev, name]
    );
  }

  const allAnalysts = ["market", "social", "news", "fundamentals"];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-100">Analyse</h1>

      {/* Analysis Form */}
      <Card title="Neue Analyse starten">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm text-gray-400">
                Ticker
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
                placeholder="z.B. NVDA"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-gray-400">Datum</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm text-gray-400">
              Analysten
            </label>
            <div className="flex flex-wrap gap-2">
              {allAnalysts.map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => toggleAnalyst(a)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                    analysts.includes(a)
                      ? "border-blue-500 bg-blue-600/20 text-blue-400"
                      : "border-gray-700 text-gray-500 hover:border-gray-600"
                  }`}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || isRunning || !ticker || !date}
            className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Wird gestartet..." : "Analyse starten"}
          </button>
        </form>
      </Card>

      {/* Task Progress */}
      {task && (
        <Card title="Analyse-Fortschritt">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-400">Status:</span>
              <StatusBadge label={task.status} />
              <span className="text-sm text-gray-500">
                Task: {task.task_id}
              </span>
            </div>

            <ProgressBar
              percent={task.progress_percent}
              label={task.message || "Verarbeitung..."}
            />

            {task.status === "completed" && task.result && (
              <div className="mt-4 space-y-3 rounded-lg border border-gray-800 bg-gray-950 p-4">
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">Signal:</span>
                  <StatusBadge
                    label={
                      (task.result as Record<string, string>).signal ?? "N/A"
                    }
                    variant="signal"
                  />
                </div>
                {(task.result as Record<string, string>).decision && (
                  <div>
                    <span className="text-sm text-gray-500">Entscheidung:</span>
                    <pre className="mt-1 max-h-60 overflow-y-auto whitespace-pre-wrap text-sm text-gray-300">
                      {(task.result as Record<string, string>).decision}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {task.status === "failed" && (
              <div className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm text-red-400">
                Fehler: {task.result ? JSON.stringify(task.result) : "Unbekannt"}
              </div>
            )}
          </div>
        </Card>
      )}

      {submitting && <Loading message="Analyse wird gestartet..." />}
    </div>
  );
}
