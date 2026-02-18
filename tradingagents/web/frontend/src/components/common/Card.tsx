interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export default function Card({ title, children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-gray-800 bg-gray-900 p-6 ${className}`}
    >
      {title && (
        <h3 className="mb-4 text-lg font-semibold text-gray-100">{title}</h3>
      )}
      {children}
    </div>
  );
}
