interface StatusBadgeProps {
  label: string;
  variant?: "signal" | "status";
  size?: "sm" | "md";
}

function signalStyle(signal: string): string {
  switch (signal?.toUpperCase()) {
    case "BUY":
      return "bg-emerald-500/15 text-emerald-400 border-emerald-500/25";
    case "SELL":
      return "bg-red-500/15 text-red-400 border-red-500/25";
    default:
      return "bg-gray-500/15 border-gray-500/25";
  }
}

function statusStyle(status: string): string {
  switch (status?.toLowerCase()) {
    case "success":
    case "completed":
      return "text-emerald-400";
    case "failure":
    case "failed":
      return "text-red-400";
    case "running":
      return "text-blue-400 animate-pulse-soft";
    default:
      return "";
  }
}

export default function StatusBadge({ label, variant = "status", size = "sm" }: StatusBadgeProps) {
  const padding = size === "sm" ? "px-2.5 py-0.5 text-xs" : "px-3 py-1 text-sm";

  if (variant === "signal") {
    return (
      <span className={`inline-flex items-center rounded-full border font-semibold ${padding} ${signalStyle(label)}`}
        style={!label || label.toUpperCase() === "HOLD" ? { color: "var(--text-secondary)" } : undefined}
      >
        {label}
      </span>
    );
  }

  return (
    <span className={`font-medium ${padding} ${statusStyle(label)}`}
      style={!statusStyle(label) ? { color: "var(--text-secondary)" } : undefined}
    >
      {label}
    </span>
  );
}
