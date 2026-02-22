interface ConfidenceMeterProps {
  value: number;
  label?: string;
}

function getColor(value: number): string {
  if (value >= 0.8) return "#34d399";
  if (value >= 0.6) return "#3b82f6";
  if (value >= 0.4) return "#f59e0b";
  return "#f87171";
}

function getLabel(value: number): string {
  if (value >= 0.8) return "Sehr hoch";
  if (value >= 0.6) return "Hoch";
  if (value >= 0.4) return "Mittel";
  return "Niedrig";
}

export default function ConfidenceMeter({ value, label }: ConfidenceMeterProps) {
  const normalized = value > 1 ? value / 100 : value;
  const percent = Math.round(normalized * 100);
  const color = getColor(normalized);

  return (
    <div className="flex items-center gap-3">
      <div
        className="relative h-2.5 w-28 overflow-hidden rounded-full"
        style={{ background: "var(--bg-card-hover)" }}
      >
        <div
          className="absolute left-0 top-0 h-full rounded-full transition-all duration-500"
          style={{ width: `${percent}%`, background: color }}
        />
      </div>
      <span className="text-sm font-medium font-mono" style={{ color }}>
        {percent}%
      </span>
      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
        {label ?? getLabel(normalized)}
      </span>
    </div>
  );
}
