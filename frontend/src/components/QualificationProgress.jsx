const steps = [
  { key: 'category', label: 'Catégorie' },
  { key: 'priority', label: 'Priorité' },
  { key: 'criticality', label: 'Criticité' },
];

export default function QualificationProgress({ qualification }) {
  if (!qualification) return null;

  const categoryDone = qualification.category && qualification.category !== 'Inconnue';
  const values = {
    category: categoryDone ? qualification.category : 'À préciser',
    priority: qualification.priority ? `Niveau ${qualification.priority}` : 'À préciser',
    criticality: qualification.criticality || 'À préciser',
  };
  const completed = [categoryDone, Boolean(qualification.priority), Boolean(qualification.criticality)].filter(Boolean).length;
  const typeLabel = Number(qualification.type) === 2 ? 'Demande' : 'Incident';

  return (
    <section className="mb-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-900" aria-label="Progression de qualification">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-slate-900 dark:text-white">Qualification en cours</p>
          <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{typeLabel} · {completed}/3 critères identifiés</p>
        </div>
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">{Math.round((completed / 3) * 100)}%</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-full rounded-full bg-autohall-blue transition-all duration-500" style={{ width: `${(completed / 3) * 100}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {steps.map(step => (
          <div key={step.key} className="min-w-0">
            <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${values[step.key] === 'À préciser' ? 'bg-slate-300 dark:bg-slate-600' : 'bg-green-500'}`} />
              {step.label}
            </div>
            <p className="mt-1 truncate text-xs font-medium text-slate-700 dark:text-slate-200" title={values[step.key]}>{values[step.key]}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
