// Number and date formatting utilities

export function formatPercent(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number, decimals = 2): string {
  return value.toFixed(decimals);
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("de-DE", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function formatDateTime(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleString("de-DE");
}

export function signalColor(signal: string): string {
  switch (signal?.toUpperCase()) {
    case "BUY":
      return "text-emerald-400";
    case "SELL":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
}

export function signalBg(signal: string): string {
  switch (signal?.toUpperCase()) {
    case "BUY":
      return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
    case "SELL":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

export function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case "success":
    case "completed":
      return "text-emerald-400";
    case "failure":
    case "failed":
      return "text-red-400";
    case "running":
      return "text-blue-400";
    default:
      return "text-gray-400";
  }
}
