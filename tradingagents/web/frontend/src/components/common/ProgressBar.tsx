interface ProgressBarProps {
  percent: number;
  label?: string;
}

export default function ProgressBar({ percent, label }: ProgressBarProps) {
  return (
    <div className="w-full">
      {label && (
        <div className="mb-1 flex justify-between text-sm text-gray-400">
          <span>{label}</span>
          <span>{percent}%</span>
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-gray-800">
        <div
          className="h-full rounded-full bg-blue-500 transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
        />
      </div>
    </div>
  );
}
