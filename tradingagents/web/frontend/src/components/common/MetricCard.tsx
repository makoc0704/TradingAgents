interface MetricCardProps {
  label: string;
  value: string;
  subtext?: string;
  color?: string;
}

export default function MetricCard({
  label,
  value,
  subtext,
  color = "text-gray-100",
}: MetricCardProps) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-gray-500">
        {label}
      </div>
      <div className={`mt-1 text-2xl font-bold ${color}`}>{value}</div>
      {subtext && <div className="mt-1 text-xs text-gray-500">{subtext}</div>}
    </div>
  );
}
