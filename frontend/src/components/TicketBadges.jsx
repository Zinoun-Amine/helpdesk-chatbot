const priorityStyles = {
  urgent: 'bg-red-100 text-red-800 ring-red-200 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-800',
  high: 'bg-orange-100 text-orange-800 ring-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-800',
  medium: 'bg-blue-100 text-blue-800 ring-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:ring-blue-800',
  low: 'bg-emerald-100 text-emerald-800 ring-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-800',
};

const criticalityStyles = {
  'très haute': 'bg-red-100 text-red-800 ring-red-200 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-800',
  haute: 'bg-orange-100 text-orange-800 ring-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:ring-orange-800',
  moyenne: 'bg-amber-100 text-amber-800 ring-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-800',
  basse: 'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700',
};

function Badge({ children, className }) {
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${className}`}>{children}</span>;
}

export function PriorityBadge({ value }) {
  const label = value || 'Medium';
  return <Badge className={priorityStyles[String(label).toLowerCase()] || priorityStyles.medium}>{label}</Badge>;
}

export function CriticalityBadge({ value }) {
  const label = value || 'moyenne';
  const key = String(label).toLowerCase();
  return <Badge className={criticalityStyles[key] || criticalityStyles.moyenne}>{label}</Badge>;
}
