interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  gradient?: boolean;
  actions?: React.ReactNode;
}

export default function Card({ title, children, className = "", gradient = false, actions }: CardProps) {
  return (
    <div
      className={`rounded-xl border p-6 transition-colors ${gradient ? "gradient-border" : ""} ${className}`}
      style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
    >
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between">
          {title && (
            <h3 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>
              {title}
            </h3>
          )}
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}
