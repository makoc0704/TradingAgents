import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div
        className="flex h-14 w-14 items-center justify-center rounded-2xl"
        style={{ background: "var(--bg-card-hover)" }}
      >
        <Icon className="h-7 w-7" style={{ color: "var(--text-muted)" }} />
      </div>
      <h3 className="mt-4 text-base font-semibold" style={{ color: "var(--text-primary)" }}>
        {title}
      </h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm" style={{ color: "var(--text-muted)" }}>
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
