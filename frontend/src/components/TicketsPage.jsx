import { useEffect, useMemo, useState } from 'react';
import * as api from '../services/api';
import TicketDraftModal from './TicketDraftModal';
import { CriticalityBadge, PriorityBadge } from './TicketBadges';

const emptyDraft = {
  title: '',
  description: '',
  category: 'General',
  priority: 'Medium',
  status: 'Open',
  ticket_type: 1,
  user_name: '',
  user_email: '',
  summary: '',
  conversation_id: null,
};

const statusOptions = ['Open', 'In Progress', 'Waiting for User', 'Resolved', 'Closed'];
const priorityOptions = ['Low', 'Medium', 'High', 'Urgent'];

export default function TicketsPage() {
  const [filters, setFilters] = useState({ search: '', status: '', priority: '' });
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [draftSaving, setDraftSaving] = useState(false);
  const [draftError, setDraftError] = useState(null);
  const [detailForm, setDetailForm] = useState(null);
  const [messageText, setMessageText] = useState('');
  const [messageSaving, setMessageSaving] = useState(false);

  const loadTickets = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchTickets(filters);
      setTickets(data);
      if (data.length && !selectedTicket) {
        setSelectedTicket(data[0].id);
      }
      if (selectedTicket && !data.some(ticket => ticket.id === selectedTicket)) {
        setSelectedTicket(data[0]?.id || null);
      }
    } catch (err) {
      setError(err.message || 'Impossible de charger les tickets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.search, filters.status, filters.priority]);

  useEffect(() => {
    if (!selectedTicket) {
      setDetailForm(null);
      return;
    }
    let ignore = false;
    const loadDetail = async () => {
      setDetailLoading(true);
      try {
        const data = await api.getTicket(selectedTicket);
        if (!ignore) setDetailForm(data);
      } catch (err) {
        if (!ignore) setError(err.message || 'Impossible de charger le ticket.');
      } finally {
        if (!ignore) setDetailLoading(false);
      }
    };
    loadDetail();
    return () => { ignore = true; };
  }, [selectedTicket]);

  const metrics = useMemo(() => ({
    total: tickets.length,
    open: tickets.filter(ticket => ticket.status === 'Open').length,
    inProgress: tickets.filter(ticket => ticket.status === 'In Progress').length,
    resolved: tickets.filter(ticket => ticket.status === 'Resolved').length,
  }), [tickets]);

  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleSaveTicket = async () => {
    if (!detailForm) return;
    try {
      setDetailLoading(true);
      const updated = await api.updateTicket(detailForm.id, {
        title: detailForm.title,
        description: detailForm.description,
        category: detailForm.category,
        priority: detailForm.priority,
        status: detailForm.status,
        user_name: detailForm.user_name,
        user_email: detailForm.user_email,
      });
      setDetailForm(updated);
      await loadTickets();
    } catch (err) {
      setError(err.message || 'Erreur lors de la mise à jour.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleAddMessage = async () => {
    if (!detailForm || !messageText.trim()) return;
    try {
      setMessageSaving(true);
      await api.addTicketMessage(detailForm.id, {
        sender_role: 'user',
        sender_name: detailForm.user_name || 'Utilisateur',
        content: messageText,
      });
      setMessageText('');
      const refreshed = await api.getTicket(detailForm.id);
      setDetailForm(refreshed);
      await loadTickets();
    } catch (err) {
      setError(err.message || 'Impossible d’ajouter le message.');
    } finally {
      setMessageSaving(false);
    }
  };

  const handleDraftSubmit = async (payload) => {
    try {
      setDraftSaving(true);
      setDraftError(null);
      const created = await api.createTicket(payload);
      setDraftOpen(false);
      setSelectedTicket(created.id);
      await loadTickets();
    } catch (err) {
      setDraftError(err.message || 'Impossible de créer le ticket.');
    } finally {
      setDraftSaving(false);
    }
  };

  return (
    <div className="flex min-h-full min-w-0 flex-col gap-4 overflow-y-auto p-2 md:p-4">
      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-autohall-blue">Tickets</div>
            <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Gestion des demandes</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">Créer, consulter, filtrer, commenter et suivre l’historique des tickets à partir des données réelles.</p>
          </div>
          <button onClick={() => setDraftOpen(true)} className="rounded-xl bg-autohall-blue px-5 py-3 text-sm font-semibold text-white hover:bg-autohall-darkBlue">
            Nouveau ticket
          </button>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-4">
          <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/50"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Total</div><div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{metrics.total}</div></div>
          <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/50"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Open</div><div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{metrics.open}</div></div>
          <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/50"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">In Progress</div><div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{metrics.inProgress}</div></div>
          <div className="rounded-2xl bg-slate-50 p-4 dark:bg-slate-800/50"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Resolved</div><div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{metrics.resolved}</div></div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_220px_220px]">
          <input name="search" value={filters.search} onChange={handleFilterChange} placeholder="Rechercher un ticket, une catégorie, un utilisateur..." className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          <select name="status" value={filters.status} onChange={handleFilterChange} className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
            <option value="">Tous les statuts</option>
            {statusOptions.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
          <select name="priority" value={filters.priority} onChange={handleFilterChange} className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
            <option value="">Toutes les priorités</option>
            {priorityOptions.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
      </div>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">{error}</div>}

      <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="min-h-0 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-5 py-4 text-sm font-semibold text-slate-900 dark:border-slate-800 dark:text-white">Liste des tickets</div>
          <div className="max-h-[calc(100vh-26rem)] overflow-y-auto">
            {loading ? (
              <div className="p-6 text-sm text-slate-500 dark:text-slate-400">Chargement...</div>
            ) : tickets.length === 0 ? (
              <div className="p-6 text-sm text-slate-500 dark:text-slate-400">Aucun ticket trouvé.</div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.16em] text-slate-500 dark:bg-slate-950 dark:text-slate-400">
                  <tr>
                    <th className="px-5 py-4">Titre</th>
                    <th className="px-5 py-4">Catégorie</th>
                    <th className="px-5 py-4">Priorité</th>
                    <th className="px-5 py-4">Criticité</th>
                    <th className="px-5 py-4">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr key={ticket.id} onClick={() => setSelectedTicket(ticket.id)} className={`cursor-pointer border-t border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50 ${selectedTicket === ticket.id ? 'bg-slate-50 dark:bg-slate-800/60' : ''}`}>
                      <td className="px-5 py-4">
                        <div className="font-semibold text-slate-900 dark:text-white">{ticket.title}</div>
                        <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">#{ticket.id} · {ticket.user_name || ticket.user_email}</div>
                      </td>
                      <td className="px-5 py-4 text-slate-600 dark:text-slate-300">{ticket.category}</td>
                      <td className="px-5 py-4"><PriorityBadge value={ticket.priority} /></td>
                      <td className="px-5 py-4"><CriticalityBadge value={ticket.criticality} /></td>
                      <td className="px-5 py-4 text-slate-600 dark:text-slate-300">{ticket.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="min-h-0 rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-5 py-4 text-sm font-semibold text-slate-900 dark:border-slate-800 dark:text-white">Détail du ticket</div>
          <div className="max-h-[calc(100vh-26rem)] overflow-y-auto p-5">
            {detailLoading && <div className="text-sm text-slate-500 dark:text-slate-400">Chargement du ticket...</div>}
            {!detailLoading && !detailForm && <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">Sélectionnez un ticket pour voir le détail.</div>}

            {detailForm && (
              <div className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Titre</span>
                    <input value={detailForm.title} onChange={(e) => setDetailForm(prev => ({ ...prev, title: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Catégorie</span>
                    <input value={detailForm.category} onChange={(e) => setDetailForm(prev => ({ ...prev, category: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Priorité</span>
                    <select value={detailForm.priority} onChange={(e) => setDetailForm(prev => ({ ...prev, priority: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                      {priorityOptions.map(option => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Statut</span>
                    <select value={detailForm.status} onChange={(e) => setDetailForm(prev => ({ ...prev, status: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                      {statusOptions.map(option => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                </div>

                <label className="space-y-2 block">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Description</span>
                  <textarea rows={5} value={detailForm.description} onChange={(e) => setDetailForm(prev => ({ ...prev, description: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
                </label>

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Utilisateur</span>
                    <input value={detailForm.user_name || ''} onChange={(e) => setDetailForm(prev => ({ ...prev, user_name: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Email</span>
                    <input value={detailForm.user_email || ''} onChange={(e) => setDetailForm(prev => ({ ...prev, user_email: e.target.value }))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
                  </label>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2"><PriorityBadge value={detailForm.priority} /><CriticalityBadge value={detailForm.criticality} /></div>
                  <button onClick={handleSaveTicket} disabled={detailLoading} className="rounded-xl bg-autohall-blue px-4 py-3 text-sm font-semibold text-white hover:bg-autohall-darkBlue disabled:opacity-60">Enregistrer</button>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                  <div className="text-sm font-semibold text-slate-900 dark:text-white">Ajouter un message</div>
                  <textarea value={messageText} onChange={(e) => setMessageText(e.target.value)} rows={4} placeholder="Réponse ou commentaire..." className="mt-3 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
                  <div className="mt-3 flex justify-end">
                    <button onClick={handleAddMessage} disabled={messageSaving} className="rounded-xl bg-autohall-green px-4 py-3 text-sm font-semibold text-white hover:bg-green-600 disabled:opacity-60">{messageSaving ? 'Envoi...' : 'Ajouter'}</button>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">Messages</div>
                    <div className="mt-3 space-y-3">
                      {(detailForm.messages || []).length ? detailForm.messages.map((message) => (
                        <div key={message.id} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/40">
                          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                            <span className="font-semibold uppercase tracking-[0.16em]">{message.sender_role}</span>
                            <span>{new Date(message.created_at).toLocaleString('fr-FR')}</span>
                          </div>
                          <div className="mt-2 text-sm text-slate-700 dark:text-slate-200">{message.content}</div>
                        </div>
                      )) : <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">Aucun message pour ce ticket.</div>}
                    </div>
                  </div>

                  <div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">Historique</div>
                    <div className="mt-3 space-y-3">
                      {(detailForm.history || []).length ? detailForm.history.map((entry) => (
                        <div key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm dark:border-slate-800 dark:bg-slate-950/40">
                          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                            <span className="font-semibold uppercase tracking-[0.16em]">{entry.field_name}</span>
                            <span>{new Date(entry.created_at).toLocaleString('fr-FR')}</span>
                          </div>
                          <div className="mt-2 text-slate-700 dark:text-slate-200">
                            <span className="font-medium">{entry.old_value || '—'}</span> <span className="text-slate-400">→</span> <span className="font-semibold">{entry.new_value || '—'}</span>
                          </div>
                        </div>
                      )) : <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">Aucun historique.</div>}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <TicketDraftModal
        isOpen={draftOpen}
        initialValues={emptyDraft}
        isSaving={draftSaving}
        error={draftError}
        onClose={() => { setDraftOpen(false); setDraftError(null); }}
        onSubmit={handleDraftSubmit}
      />
    </div>
  );
}
