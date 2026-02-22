interface SkeletonProps {
  height?: string;
  className?: string;
  lines?: number;
}

export default function Skeleton({ height = "h-4", className = "", lines }: SkeletonProps) {
  if (lines) {
    return (
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`skeleton ${height} ${i === lines - 1 ? "w-2/3" : "w-full"}`}
          />
        ))}
      </div>
    );
  }

  return <div className={`skeleton ${height} ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div
      className="rounded-xl border p-4 space-y-3"
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      <div className="skeleton h-3 w-1/3" />
      <div className="skeleton h-6 w-2/3" />
      <div className="skeleton h-3 w-1/2" />
    </div>
  );
}
