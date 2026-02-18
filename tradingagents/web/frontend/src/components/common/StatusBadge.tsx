import { signalBg, statusColor } from "../../utils/format";

interface StatusBadgeProps {
  label: string;
  variant?: "signal" | "status";
}

export default function StatusBadge({
  label,
  variant = "status",
}: StatusBadgeProps) {
  if (variant === "signal") {
    return (
      <span
        className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-semibold ${signalBg(label)}`}
      >
        {label}
      </span>
    );
  }
  return (
    <span className={`text-sm font-medium ${statusColor(label)}`}>
      {label}
    </span>
  );
}
