import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Search } from "lucide-react";
import Card from "../components/common/Card";
import StatusBadge from "../components/common/StatusBadge";
import ProgressBar from "../components/common/ProgressBar";
import Skeleton from "../components/common/Skeleton";
import ConfidenceMeter from "../components/charts/ConfidenceMeter";
import { runAnalysis } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import type { TaskStatus } from "../types";

export default function AnalysisPage() {
  const [ticker, setTicker] = useState("NVDA");
  const [date, setDate] = useState("2024-06-05");
  const [analysts, setAnalysts] = useState(["market", "fundamentals"]);
  const [task, setTask] = useState<TaskStatus | null>(null);
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
      result: (lastMessage.result as Record<string, unknown>) ?? task.result,
    };
    if (updated.status !== task.status || updated.progress_percent !== task.progress_percent) {
      setTask(updated);
    }
  }, [lastMessage]);

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
    if (res.success && res.data) setTask(res.data);
  }

  function toggleAnalyst(name: string) {
    setAnalysts((prev) =>
      prev.includes(name) ? prev.filter((a) => a !== name) : [...prev, name]
    );
  }

  const allAnalysts = ["market", "social", "news", "fundamentals"];
  const resultData = task?.result as Record<string, string> | undefined;
  const signal = resultData?.signal;
  const confidence = parseFloat(resultData?.confidence ?? "") || 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>Analyse</h1>

      {/* Form */}
      <Card title="Neue Analyse starten">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>Ticker</label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
                placeholder="z.B. NVDA"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm" style={{ color: "var(--text-secondary)" }}>Datum</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm"
                style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-primary)" }}
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm" style={{ color: "var(--text-secondary)" }}>Analysten</label>
            <div className="flex flex-wrap gap-2">
              {allAnalysts.map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => toggleAnalyst(a)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                    analysts.includes(a)
                      ? "border-blue-500 bg-blue-600/20 text-blue-400"
                      : "hover:border-[var(--border-hover)]"
                  }`}
                  style={
                    !analysts.includes(a)
                      ? { borderColor: "var(--border)", color: "var(--text-muted)" }
                      : undefined
                  }
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || isRunning || !ticker.trim() || !date}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            {submitting ? "Wird gestartet..." : "Analyse starten"}
          </button>
        </form>
      </Card>

      {/* Progress */}
      {task && (
        <Card title="Analyse-Fortschritt">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <span className="text-sm" style={{ color: "var(--text-secondary)" }}>Status:</span>
              <StatusBadge label={task.status} />
              <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                {task.task_id}
              </span>
            </div>

            <ProgressBar percent={task.progress_percent} label={task.message || "Verarbeitung..."} />

            {task.status === "completed" && resultData && (
              <div className="mt-4 space-y-4">
                <div className="flex items-center gap-6">
                  {signal && <StatusBadge label={signal} variant="signal" size="md" />}
                  {confidence > 0 && <ConfidenceMeter value={confidence} />}
                  <Link
                    to={`/agent-flow/${ticker.toUpperCase()}/${date}`}
                    className="ml-auto flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Agent Flow anzeigen
                  </Link>
                </div>

                {resultData.decision && (
                  <div
                    className="rounded-lg border p-4"
                    style={{ background: "var(--bg-primary)", borderColor: "var(--border)" }}
                  >
                    <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
                      Entscheidung
                    </span>
                    <pre
                      className="mt-2 max-h-60 overflow-y-auto whitespace-pre-wrap text-sm"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {resultData.decision}
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

      {submitting && (
        <div className="space-y-3">
          <Skeleton height="h-4" className="w-3/4" />
          <Skeleton height="h-4" className="w-1/2" />
        </div>
      )}
    </div>
  );
}
