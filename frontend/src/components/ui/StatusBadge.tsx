const STATUS_STYLES: Record<string, string> = {
  waiting: "bg-amber-100 text-amber-800",
  called: "bg-blue-100 text-blue-800",
  serving: "bg-indigo-100 text-indigo-800",
  completed: "bg-emerald-100 text-emerald-800",
  skipped: "bg-slate-200 text-slate-600",
  absent: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${style}`}>
      {status}
    </span>
  );
}
