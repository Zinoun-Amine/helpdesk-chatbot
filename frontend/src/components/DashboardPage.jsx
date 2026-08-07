import { useEffect, useMemo, useState } from 'react';
import * as api from '../services/api';

const periods = [
  { id: 'today', label: "Aujourd'hui" },
  { id: '7d', label: '7 derniers jours' },
  { id: '30d', label: '30 derniers jours' },
  { id: '90d', label: '3 derniers mois' },
];

function MetricCard({ label, value, hint }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-3 text-3xl font-bold text-slate-900 dark:text-white">{value}</div>
      {hint && <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">{hint}</div>}
    </div>
  );
}

function MiniBarChart({ title, data = [], valueKey = 'count', labelKey = 'day' }) {
  const max = Math.max(...data.map(item => Number(item[valueKey]) || 0), 1);
  const [hoveredIndex, setHoveredIndex] = useState(null);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">{title}</div>
      <div className="space-y-3">
        {data.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">Aucune donnée sur la période.</div>
        ) : data.map((item, index) => {
          const value = Number(item[valueKey]) || 0;
          const width = `${Math.max((value / max) * 100, 6)}%`;
          const label = item[labelKey] ? new Date(item[labelKey]).toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: '2-digit' }) : '—';
          return (
            <div key={`${item[labelKey]}-${value}`} onMouseEnter={() => setHoveredIndex(index)} onMouseLeave={() => setHoveredIndex(null)} className={`group relative grid grid-cols-[84px_1fr_52px] items-center gap-3 rounded-lg p-1 text-sm transition ${hoveredIndex === index ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}>
              <div className="text-slate-500 dark:text-slate-400">{label}</div>
              <div className="h-3 rounded-full bg-slate-100 dark:bg-slate-800">
                <div className={`h-3 rounded-full bg-gradient-to-r from-autohall-blue to-autohall-green transition-all duration-300 ${hoveredIndex === index ? 'brightness-110' : ''}`} style={{ width }} />
              </div>
              <div className="relative text-right font-semibold text-slate-700 dark:text-slate-200">{value}{hoveredIndex === index && <span className="absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-[10px] font-normal text-white shadow-lg dark:bg-white dark:text-slate-900">{label} · {value}</span>}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [period, setPeriod] = useState('30d');
  const [customRange, setCustomRange] = useState({ start: '', end: '' });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = period === 'custom' && customRange.start && customRange.end
          ? await api.getDashboard('custom', customRange.start, customRange.end)
          : await api.getDashboard(period);
        if (!ignore) setData(payload);
      } catch (err) {
        if (!ignore) setError(err.message || 'Impossible de charger le dashboard.');
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    load();
    return () => { ignore = true; };
  }, [period, customRange.start, customRange.end]);

  const totals = data?.totals || {};
  const charts = data?.charts || {};

  const providerCards = useMemo(() => data?.llm_providers || [], [data]);

  return (
    <div className="space-y-6 p-2 md:p-4">
      <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-autohall-blue">Dashboard</div>
          <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Vue opérationnelle du chatbot</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">Mesures réelles issues des conversations, tickets, historique runtime et suivi des providers LLM.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {periods.map((item) => (
            <button key={item.id} onClick={() => setPeriod(item.id)} className={`rounded-full px-4 py-2 text-sm font-medium transition ${period === item.id ? 'bg-autohall-blue text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'}`}>
              {item.label}
            </button>
          ))}
          <button onClick={() => setPeriod('custom')} className={`rounded-full px-4 py-2 text-sm font-medium transition ${period === 'custom' ? 'bg-autohall-blue text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'}`}>
            Personnalisée
          </button>
        </div>
      </div>

      {period === 'custom' && (
        <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 md:grid-cols-3">
          <label className="space-y-2 text-sm">
            <span className="font-medium text-slate-700 dark:text-slate-200">Début</span>
            <input type="datetime-local" value={customRange.start} onChange={(e) => setCustomRange(prev => ({ ...prev, start: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>
          <label className="space-y-2 text-sm">
            <span className="font-medium text-slate-700 dark:text-slate-200">Fin</span>
            <input type="datetime-local" value={customRange.end} onChange={(e) => setCustomRange(prev => ({ ...prev, end: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>
          <div className="flex items-end">
            <button onClick={() => setPeriod('custom')} className="w-full rounded-xl bg-autohall-darkBlue px-4 py-3 text-sm font-semibold text-white">Appliquer</button>
          </div>
        </div>
      )}

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">{error}</div>}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Conversations" value={loading ? '...' : totals.conversations ?? 0} hint="Total sur la période" />
        <MetricCard label="Tickets" value={loading ? '...' : totals.tickets ?? 0} hint={`Ouverts: ${totals.open_tickets ?? 0} | En cours: ${totals.in_progress_tickets ?? 0}`} />
        <MetricCard label="Taux de résolution" value={loading ? '...' : `${totals.resolution_rate ?? 0}%`} hint={`Temps moyen: ${totals.avg_resolution_hours ?? 0} h`} />
        <MetricCard label="Utilisateurs actifs" value={loading ? '...' : totals.active_users ?? 0} hint="Basé sur les conversations visibles" />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <MiniBarChart title="Activité du chatbot" data={charts.activity || []} />
        <MiniBarChart title="Évolution des tickets" data={charts.ticket_activity || []} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">Tickets par statut</div>
          <div className="space-y-3">
            {(charts.ticket_status || []).map((item) => (
              <div key={item.status} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm dark:bg-slate-800/50">
                <span className="font-medium text-slate-700 dark:text-slate-200">{item.status}</span>
                <span className="font-semibold text-slate-900 dark:text-white">{item.count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">Tickets par priorité</div>
          <div className="space-y-3">
            {(charts.ticket_priority || []).map((item) => (
              <div key={item.priority} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm dark:bg-slate-800/50">
                <span className="font-medium text-slate-700 dark:text-slate-200">{item.priority}</span>
                <span className="font-semibold text-slate-900 dark:text-white">{item.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">Provider LLM</div>
          <div className="grid gap-4 lg:grid-cols-3">
            {providerCards.map((provider) => (
              <div key={provider.provider} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/60">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">{provider.provider}</div>
                    <div className="mt-1 text-lg font-bold text-slate-900 dark:text-white">{provider.label}</div>
                  </div>
                  <div className="h-3 w-3 rounded-full bg-autohall-green" />
                </div>
                <div className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                  <div className="flex justify-between"><span>Requêtes</span><span className="font-semibold">{provider.requests}</span></div>
                  <div className="flex justify-between"><span>Succès</span><span className="font-semibold">{provider.successes}</span></div>
                  <div className="flex justify-between"><span>Erreurs</span><span className="font-semibold">{provider.errors}</span></div>
                  <div className="flex justify-between"><span>Temps moyen</span><span className="font-semibold">{provider.avg_response_ms} ms</span></div>
                  <div className="flex justify-between"><span>Fallbacks</span><span className="font-semibold">{provider.fallbacks}</span></div>
                  <div className="flex justify-between"><span>Utilisation</span><span className="font-semibold">{provider.utilization}%</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 text-sm font-semibold text-slate-900 dark:text-white">Conversations récentes</div>
          <div className="space-y-3">
            {(data?.recent_conversations || []).map((conversation) => (
              <div key={conversation.id} className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/50">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900 dark:text-white">{conversation.user_name || 'Utilisateur inconnu'}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">#{conversation.id} · {conversation.current_state}</div>
                  </div>
                  <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{conversation.message_count} msgs</span>
                </div>
              </div>
            ))}
            {!(data?.recent_conversations || []).length && <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">Aucune conversation disponible.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
