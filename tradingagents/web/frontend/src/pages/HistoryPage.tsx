import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Clock, ExternalLink, Search } from "lucide-react";
import Card from "../components/common/Card";
import StatusBadge from "../components/common/StatusBadge";
import Skeleton from "../components/common/Skeleton";
import EmptyState from "../components/common/EmptyState";
import { listTickers, listTickerDates, getAnalysisResult } from "../api/client";
import { formatDate } from "../utils/format";
import type { HistoryEntry } from "../types";

export default function HistoryPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loadingEntries, setLoadingEntries] = useState(false);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    loadTickers();
  }, []);

  async function loadTickers() {
    setLoading(true);
    const res = await listTickers();
    if (res.success && res.data) {
      setTickers(res.data);
      if (res.data.length > 0) {
        await loadAllEntries(res.data);
      }
    }
    setLoading(false);
  }

  async function loadAllEntries(tickerList: string[]) {
    setLoadingEntries(true);
    const allEntries: HistoryEntry[] = [];

    for (const ticker of tickerList) {
      const datesRes = await listTickerDates(ticker);
      if (datesRes.success && datesRes.data) {
        for (const date of datesRes.data) {
          const resultRes = await getAnalysisResult(ticker, date);
          if (resultRes.success && resultRes.data) {
            const r = resultRes.data;
            allEntries.push({
              ticker: r.ticker,
              date: r.date,
              signal: r.signal ?? "N/A",
              confidence: r.confidence ?? "N/A",
              has_debate: !!(r.investment_debate || r.risk_debate),
            });
          } else {
            allEntries.push({
              ticker,
              date,
              signal: "N/A",
              confidence: "N/A",
              has_debate: false,
            });
          }
        }
      }
    }

    allEntries.sort((a, b) => b.date.localeCompare(a.date));
    setEntries(allEntries);
    setLoadingEntries(false);
  }

  const filtered = filter
    ? entries.filter(
        (e) =>
          e.ticker.toLowerCase().includes(filter.toLowerCase()) ||
          e.signal.toLowerCase().includes(filter.toLowerCase())
      )
    : entries;

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton height="h-8" className="w-1/4" />
        <Skeleton lines={8} />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
          Analyse-Archiv
        </h1>
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
          {entries.length} Ergebnisse
        </span>
      </div>

      {tickers.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="Noch keine Analysen"
          description="Starte eine Analyse auf der Analyse-Seite, um hier Ergebnisse zu sehen."
        />
      ) : (
        <>
          {/* Filter */}
          <Card>
            <div className="flex items-center gap-3">
              <Search className="h-4 w-4" style={{ color: "var(--text-muted)" }} />
              <input
                type="text"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Ticker oder Signal filtern..."
                className="flex-1 bg-transparent text-sm outline-none"
                style={{ color: "var(--text-primary)" }}
              />
            </div>
          </Card>

          {/* Entries Table */}
          {loadingEntries ? (
            <Skeleton lines={8} />
          ) : (
            <Card>
              {filtered.length === 0 ? (
                <div className="py-6 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                  Keine Ergebnisse gefunden.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                        <th className="pb-3 font-medium">Ticker</th>
                        <th className="pb-3 font-medium">Datum</th>
                        <th className="pb-3 font-medium">Signal</th>
                        <th className="pb-3 font-medium">Konfidenz</th>
                        <th className="pb-3 font-medium">Debatte</th>
                        <th className="pb-3 font-medium">Aktionen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((entry) => (
                        <tr key={`${entry.ticker}-${entry.date}`} className="border-b" style={{ borderColor: "var(--border)" }}>
                          <td className="py-3 font-medium" style={{ color: "var(--text-primary)" }}>
                            {entry.ticker}
                          </td>
                          <td className="py-3" style={{ color: "var(--text-secondary)" }}>
                            {formatDate(entry.date)}
                          </td>
                          <td className="py-3">
                            <StatusBadge label={entry.signal} variant="signal" />
                          </td>
                          <td className="py-3 font-mono" style={{ color: "var(--text-secondary)" }}>
                            {entry.confidence}
                          </td>
                          <td className="py-3">
                            {entry.has_debate ? (
                              <span className="text-emerald-400 text-xs">Ja</span>
                            ) : (
                              <span style={{ color: "var(--text-muted)" }}>–</span>
                            )}
                          </td>
                          <td className="py-3">
                            <div className="flex gap-2">
                              <Link
                                to={`/agent-flow/${entry.ticker}/${entry.date}`}
                                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Agent Flow
                              </Link>
                              <Link
                                to={`/risk/${entry.ticker}/${entry.date}`}
                                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Risk
                              </Link>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
