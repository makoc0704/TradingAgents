import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronRight, MessageSquare, Gavel } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Card from "../components/common/Card";
import StatusBadge from "../components/common/StatusBadge";
import Skeleton from "../components/common/Skeleton";
import ConfidenceMeter from "../components/charts/ConfidenceMeter";
import { getAnalysisResult } from "../api/client";
import type { AnalysisResult, DebateArgument } from "../types";

const FLOW_STEPS = [
  { key: "market_report", label: "Markt-Analyst", color: "#3b82f6" },
  { key: "sentiment_report", label: "Sentiment-Analyst", color: "#8b5cf6" },
  { key: "news_report", label: "News-Analyst", color: "#f59e0b" },
  { key: "fundamentals_report", label: "Fundamental-Analyst", color: "#10b981" },
  { key: "investment_debate", label: "Investment-Debatte", color: "#ec4899" },
  { key: "risk_debate", label: "Risiko-Debatte", color: "#ef4444" },
  { key: "final_decision", label: "Trader-Entscheidung", color: "#06b6d4" },
] as const;

export default function AgentFlowPage() {
  const { ticker, date } = useParams<{ ticker: string; date: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!ticker || !date) return;
    getAnalysisResult(ticker, date).then((res) => {
      if (res.success && res.data) setResult(res.data);
      setLoading(false);
    });
  }, [ticker, date]);

  function toggleExpand(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton height="h-8" className="w-1/3" />
        <Skeleton lines={6} />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="space-y-4">
        <Link to="/history" className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300">
          <ArrowLeft className="h-4 w-4" /> Zurück
        </Link>
        <Card>
          <p style={{ color: "var(--text-muted)" }}>
            Keine Ergebnisse gefunden für {ticker} / {date}.
          </p>
        </Card>
      </div>
    );
  }

  const reportValue = (key: string): string | null => {
    const val = result[key as keyof AnalysisResult];
    if (typeof val === "string") return val;
    return null;
  };

  const confidence = parseFloat(result.confidence ?? "") || 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <Link to="/history" className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300">
          <ArrowLeft className="h-4 w-4" /> Zurück
        </Link>
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Agent Flow: {ticker}
        </h1>
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>{date}</span>
      </div>

      {/* Signal + Confidence Summary */}
      <Card gradient>
        <div className="flex items-center gap-6">
          <StatusBadge label={result.signal ?? "N/A"} variant="signal" size="md" />
          {confidence > 0 && <ConfidenceMeter value={confidence} />}
        </div>
      </Card>

      {/* Flow Pipeline */}
      <div className="space-y-3">
        {FLOW_STEPS.map((step, idx) => {
          const isExpanded = expanded.has(step.key);
          const isDebate = step.key === "investment_debate" || step.key === "risk_debate";
          const report = reportValue(step.key);
          const debate = isDebate
            ? (result[step.key as "investment_debate" | "risk_debate"] ?? null)
            : null;
          const hasContent = !!report || !!debate;

          return (
            <div key={step.key}>
              {/* Connector line */}
              {idx > 0 && (
                <div className="ml-6 h-4 border-l-2" style={{ borderColor: "var(--border)" }} />
              )}

              <button
                onClick={() => hasContent && toggleExpand(step.key)}
                disabled={!hasContent}
                className="flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors hover:border-[var(--border-hover)] disabled:opacity-50 disabled:cursor-default"
                style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
              >
                <div
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white"
                  style={{ background: step.color }}
                >
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    {step.label}
                  </span>
                  {!hasContent && (
                    <span className="ml-2 text-xs" style={{ color: "var(--text-muted)" }}>
                      (nicht verfügbar)
                    </span>
                  )}
                </div>
                {hasContent && (
                  isExpanded
                    ? <ChevronDown className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
                    : <ChevronRight className="h-4 w-4 shrink-0" style={{ color: "var(--text-muted)" }} />
                )}
              </button>

              {/* Expanded content */}
              {isExpanded && report && (
                <div
                  className="ml-6 mt-2 rounded-lg border p-4 prose prose-sm prose-invert max-w-none"
                  style={{ background: "var(--bg-primary)", borderColor: "var(--border)", color: "var(--text-secondary)" }}
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
                </div>
              )}

              {isExpanded && debate && (
                <DebateView debate={debate} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DebateView({ debate }: { debate: { bull_arguments?: DebateArgument[]; bear_arguments?: DebateArgument[]; judge_verdict?: string } }) {
  const maxRounds = Math.max(
    debate.bull_arguments?.length ?? 0,
    debate.bear_arguments?.length ?? 0
  );

  return (
    <div className="ml-6 mt-2 space-y-3">
      {Array.from({ length: maxRounds }).map((_, i) => {
        const bull = debate.bull_arguments?.[i];
        const bear = debate.bear_arguments?.[i];
        return (
          <div key={i} className="space-y-2">
            {bull && (
              <div className="flex gap-3 animate-slide-in">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/15">
                  <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
                </div>
                <div
                  className="flex-1 rounded-lg border p-3 text-sm"
                  style={{ background: "var(--bg-card)", borderColor: "var(--border)", color: "var(--text-secondary)" }}
                >
                  <span className="mb-1 block text-xs font-semibold text-emerald-400">
                    Bull (Runde {(bull.round ?? i) + 1})
                  </span>
                  {bull.content}
                </div>
              </div>
            )}
            {bear && (
              <div className="flex gap-3 animate-slide-in">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-red-500/15">
                  <MessageSquare className="h-3.5 w-3.5 text-red-400" />
                </div>
                <div
                  className="flex-1 rounded-lg border p-3 text-sm"
                  style={{ background: "var(--bg-card)", borderColor: "var(--border)", color: "var(--text-secondary)" }}
                >
                  <span className="mb-1 block text-xs font-semibold text-red-400">
                    Bear (Runde {(bear.round ?? i) + 1})
                  </span>
                  {bear.content}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {debate.judge_verdict && (
        <div className="flex gap-3 animate-slide-in">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-500/15">
            <Gavel className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <div
            className="flex-1 rounded-lg border-2 p-3 text-sm"
            style={{ background: "var(--bg-card)", borderColor: "rgba(245, 158, 11, 0.3)", color: "var(--text-secondary)" }}
          >
            <span className="mb-1 block text-xs font-semibold text-amber-400">Urteil des Richters</span>
            {debate.judge_verdict}
          </div>
        </div>
      )}
    </div>
  );
}
