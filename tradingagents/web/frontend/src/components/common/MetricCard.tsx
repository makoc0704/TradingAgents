interface MetricCardProps {
  label: string;
  value: string;
  subtext?: string;
  color?: string;
  trend?: "up" | "down" | "neutral";
  mono?: boolean;
}

export default function MetricCard({
  label,
  value,
  subtext,
  color,
  trend,
  mono = false,
}: MetricCardProps) {
  const trendColors = {
    up: "text-emerald-400",
    down: "text-red-400",
    neutral: "",
  };

  const valueColor = color ?? (trend ? trendColors[trend] : "");

  return (
    <div
      className="rounded-xl border p-4 transition-colors hover:border-[var(--border-hover)]"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <div className={`mt-1.5 text-2xl font-bold ${valueColor} ${mono ? "font-mono" : ""}`}
        style={!valueColor ? { color: "var(--text-primary)" } : undefined}
      >
        {value}
      </div>
      {subtext && (
        <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
          {subtext}
        </div>
      )}
    </div>
  );
}
