interface LoadingProps {
  message?: string;
}

export default function Loading({ message = "Loading..." }: LoadingProps) {
  return (
    <div className="flex items-center gap-3 py-8 text-gray-400">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400" />
      <span>{message}</span>
    </div>
  );
}
