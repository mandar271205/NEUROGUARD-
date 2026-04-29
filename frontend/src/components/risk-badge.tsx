const labels = ["Normal", "High-Stress", "High-Risk"];
const classes = [
  "bg-emerald-100 text-emerald-800 ring-emerald-200",
  "bg-amber-100 text-amber-800 ring-amber-200",
  "bg-rose-100 text-rose-800 ring-rose-200"
];

export function RiskBadge({ level }: { level?: number | null }) {
  if (level === undefined || level === null) {
    return (
      <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-semibold text-zinc-600 ring-1 ring-zinc-200">
        No result
      </span>
    );
  }

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${classes[level] || classes[0]}`}>
      {labels[level] || "Normal"}
    </span>
  );
}
