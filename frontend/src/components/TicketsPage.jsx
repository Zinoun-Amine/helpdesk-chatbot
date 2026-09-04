import { useEffect, useMemo, useRef, useState } from 'react';
import * as api from '../services/api';
import TicketDraftModal from './TicketDraftModal';
import EmailDraft from './EmailDraft';
import { CriticalityBadge, PriorityBadge } from './TicketBadges';
import { useAuth } from '../hooks/useAuth';

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

const statusOptions = ['In Progress', 'Resolved'];
const priorityOptions = ['Low', 'Medium', 'High', 'Urgent'];

export default function TicketsPage() {
  const { user } = useAuth();
  const isTechnician = user?.role === 'technician';
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
  const [technicians, setTechnicians] = useState([]);
  const [reassigning, setReassigning] = useState(false);
  const [messageText, setMessageText] = useState('');
  const [messageSaving, setMessageSaving] = useState(false);
  const [emailDraft, setEmailDraft] = useState(null);
  const [emailDraftLoading, setEmailDraftLoading] = useState(false);
  const [emailDraftError, setEmailDraftError] = useState(null);
  const [emailSentAt, setEmailSentAt] = useState(null);
  const emailSentTimeoutRef = useRef(null);

  const loadTickets = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        ...filters,
        ...((user?.role || 'user') === 'admin' ? {} : { user_email: user?.email }),
      };
      const data = await api.searchTickets(params);
      setTickets(data);
      if (selectedTicket && !data.some(ticket => ticket.id === selectedTicket)) {
        setSelectedTicket(null);
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
  }, [filters.search, filters.status, filters.priority, user]);

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

  useEffect(() => {
    if (!detailForm) {
      setEmailDraft(null);
      return;
    }
    let ignore = false;
    const loadEmailDraft = async () => {
      setEmailDraftLoading(true);
      setEmailDraftError(null);
      try {
        const data = await api.getTicketEmailDraft(detailForm.id);
        if (!ignore) setEmailDraft(data);
      } catch (err) {
        if (!ignore) setEmailDraftError(err.message || 'Impossible de charger le brouillon d\'e-mail.');
      } finally {
        if (!ignore) setEmailDraftLoading(false);
      }
    };
    loadEmailDraft();
    return () => { ignore = true; };
  }, [detailForm]);

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

  const loadTechnicians = async () => {
    try {
      const data = await api.getTechnicians();
      setTechnicians(data);
    } catch (err) {
      setError(err.message || 'Impossible de charger les techniciens.');
    }
  };

  useEffect(() => {
    loadTechnicians();
  }, []);

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

  const handleReassignTicket = async () => {
    if (!detailForm) return;
    const selectedTechnician = technicians.find((tech) => String(tech.id) === String(detailForm.assigned_to_id));
    if (!selectedTechnician) return;

    try {
      setReassigning(true);
      const updated = await api.assignTicket(detailForm.id, {
        technician_id: selectedTechnician.id,
        technician_name: selectedTechnician.full_name,
        technician_email: selectedTechnician.email,
        assigned_by: 'Admin',
        reason: 'Affectation manuelle depuis le ticket',
      });
      setDetailForm(updated);
      await loadTickets();
      try {
        const draft = await api.getTicketEmailDraft(updated.id);
        if (draft && draft.id && draft.status !== 'sent') {
          await api.sendEmailDraft(draft.id);
          setEmailDraft({ ...draft, status: 'sent' });
          const now = new Date();
          setEmailSentAt(now);
          if (emailSentTimeoutRef.current) clearTimeout(emailSentTimeoutRef.current);
          emailSentTimeoutRef.current = setTimeout(() => setEmailSentAt(null), 5000);
        }
      } catch (err) {
        setError(err.message || 'Impossible d\'envoyer le mail au technicien.');
      }
    } catch (err) {
      setError(err.message || 'Impossible de réaffecter le ticket.');
    } finally {
      setReassigning(false);
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
    <div className="flex min-h-full min-w-0 flex-col gap-3 overflow-y-auto p-2 md:p-3">
      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-autohall-blue">Tickets</div>
            <h2 className="mt-1 text-xl font-bold text-slate-900 dark:text-white">Gestion des demandes</h2>
            <p className="mt-1 max-w-2xl text-xs text-slate-500 dark:text-slate-400">Créer, consulter, filtrer, commenter et suivre l’historique des tickets à partir des données réelles.</p>
          </div>
          {!isTechnician && <button onClick={() => setDraftOpen(true)} className="rounded-xl bg-autohall-blue px-4 py-2 text-xs font-semibold text-white hover:bg-autohall-darkBlue">
            Nouveau ticket
          </button>}
        </div>

        <div className="mt-3 grid gap-2 md:grid-cols-4">
          <div className="rounded-2xl bg-slate-50 p-2 dark:bg-slate-800/50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Total</div>
            <div className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">{metrics.total}</div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-2 dark:bg-slate-800/50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Open</div>
            <div className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">{metrics.open}</div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-2 dark:bg-slate-800/50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">In Progress</div>
            <div className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">{metrics.inProgress}</div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-2 dark:bg-slate-800/50">
            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Resolved</div>
            <div className="mt-0.5 text-xl font-bold text-slate-900 dark:text-white">{metrics.resolved}</div>
          </div>
        </div>

        <div className="mt-3 grid gap-2 lg:grid-cols-[1fr_180px_180px]">
          <input
            name="search"
            value={filters.search}
            onChange={handleFilterChange}
            placeholder="Rechercher un ticket, une catégorie, un utilisateur..."
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          />
          <select
            name="status"
            value={filters.status}
            onChange={handleFilterChange}
            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          >
            <option value="">Tous les statuts</option>
            {statusOptions.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
          <select
            name="priority"
            value={filters.priority}
            onChange={handleFilterChange}
            className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          >
            <option value="">Toutes les priorités</option>
            {priorityOptions.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
      </div>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">{error}</div>}

      <div className={`grid min-h-0 flex-1 gap-4 ${selectedTicket ? 'xl:grid-cols-[1fr_2fr]' : 'xl:grid-cols-1'}`}>
        <div className="min-h-0 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-lg dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-4 py-3 text-xs font-semibold text-slate-900 dark:border-slate-800 dark:text-white">
            Liste des tickets
          </div>
          <div className="max-h-[calc(100vh-22rem)] overflow-y-auto">
            {loading ? (
              <div className="p-4 text-sm text-slate-500 dark:text-slate-400">Chargement...</div>
            ) : tickets.length === 0 ? (
              <div className="p-4 text-sm text-slate-500 dark:text-slate-400">Aucun ticket trouvé.</div>
            ) : (
              <table className="w-full text-left text-sm"> {/* ← changed to text-sm */}
                <thead className="sticky top-0 bg-slate-50 text-xs uppercase tracking-[0.16em] text-slate-500 dark:bg-slate-950 dark:text-slate-400"> {/* ← headers text-xs */}
                  <tr>
                    <th className="px-4 py-2.5">Titre</th> {/* slightly more padding */}
                    <th className="px-4 py-2.5">Catégorie</th>
                    <th className="px-4 py-2.5">Priorité</th>
                    <th className="px-4 py-2.5">Criticité</th>
                    <th className="px-4 py-2.5">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((ticket) => (
                    <tr
                      key={ticket.id}
                      onClick={() => setSelectedTicket(ticket.id)}
                      className={`cursor-pointer border-t border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50 ${
                        selectedTicket === ticket.id ? 'bg-slate-50 dark:bg-slate-800/60' : ''
                      }`}
                    >
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-slate-900 dark:text-white">{ticket.title}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">#{ticket.id} · {ticket.user_name || ticket.user_email}</div>
                      </td>
                      <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{ticket.category}</td>
                      <td className="px-4 py-2.5"><PriorityBadge value={ticket.priority} /></td>
                      <td className="px-4 py-2.5"><CriticalityBadge value={ticket.criticality} /></td>
                      <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">
                        <div className="font-medium">{ticket.status}</div>
                        <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                          {ticket.assigned_to_name ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">
                              {ticket.assigned_to_name}
                            </span>
                          ) : (
                            <span className="text-slate-400">Non assigné</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {selectedTicket && (
          <div className="min-h-0 rounded-3xl border border-slate-200 bg-white shadow-lg dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-200 px-4 py-3 flex items-center justify-between text-sm font-semibold text-slate-900 dark:border-slate-800 dark:text-white">
              <div>Détail du ticket</div>
              <div className="flex items-center gap-2">
                <button onClick={() => setSelectedTicket(null)} className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400">Fermer</button>
              </div>
            </div>
            <div className="max-h-[calc(100vh-22rem)] overflow-y-auto p-4">
              {detailLoading && <div className="text-sm text-slate-500 dark:text-slate-400">Chargement du ticket...</div>}
              {!detailLoading && !detailForm && <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">Sélectionnez un ticket pour voir le détail.</div>}

              {detailForm && (
                <div className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Titre</span>
                      <input
                        value={detailForm.title}
                        onChange={(e) => setDetailForm(prev => ({ ...prev, title: e.target.value }))}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      />
                    </label>
                    <label className="space-y-1">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Catégorie</span>
                      <input
                        value={detailForm.category}
                        onChange={(e) => setDetailForm(prev => ({ ...prev, category: e.target.value }))}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      />
                    </label>
                    <label className="space-y-1">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Priorité</span>
                      <select
                        value={detailForm.priority}
                        onChange={(e) => setDetailForm(prev => ({ ...prev, priority: e.target.value }))}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      >
                        {priorityOptions.map(option => <option key={option} value={option}>{option}</option>)}
                      </select>
                    </label>
                    <label className="space-y-1">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Statut</span>
                      <select
                        value={detailForm.status}
                        onChange={(e) => setDetailForm(prev => ({ ...prev, status: e.target.value }))}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      >
                        {statusOptions.map(option => <option key={option} value={option}>{option}</option>)}
                      </select>
                    </label>
                  </div>

                  <label className="block space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Description</span>
                    <textarea
                      rows={4}
                      value={detailForm.description}
                      onChange={(e) => setDetailForm(prev => ({ ...prev, description: e.target.value }))}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                    />
                  </label>

                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Utilisateur</span>
                      <input
                        value={detailForm.user_name || ''}
                        onChange={(e) => setDetailForm(prev => ({ ...prev, user_name: e.target.value }))}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      />
                    </label>
                    <label className="space-y-1">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Email</span>
                      <input
                        value={detailForm.user_email || ''}
                        onChange={(e) => setDetailForm(prev => ({ ...prev, user_email: e.target.value }))}
                        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                      />
                    </label>
                  </div>

                  <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/40 dark:bg-blue-950/20">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-700 dark:text-blue-300">Technicien assigné</div>
                    {detailForm.assigned_to_name ? (
                      <div className="mt-1 space-y-1">
                        <div className="text-base font-semibold text-slate-900 dark:text-white">{detailForm.assigned_to_name}</div>
                        <div className="text-sm text-slate-600 dark:text-slate-300">{detailForm.assigned_to_email || 'Email non renseigné'}</div>
                      </div>
                    ) : (
                      <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">Aucun technicien assigné pour ce ticket.</div>
                    )}

                    {!isTechnician && <div className="mt-3 space-y-3">
                      <label className="block space-y-1">
                        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">Réaffecter</span>
                        <select
                          value={detailForm.assigned_to_id ?? ''}
                          onChange={(e) =>
                            setDetailForm(prev => ({
                              ...prev,
                              assigned_to_id: Number(e.target.value),
                              assigned_to_name: technicians.find((tech) => String(tech.id) === e.target.value)?.full_name || prev.assigned_to_name,
                              assigned_to_email: technicians.find((tech) => String(tech.id) === e.target.value)?.email || prev.assigned_to_email,
                            }))
                          }
                          className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                        >
                          <option value="">Choisir un technicien</option>
                          {technicians.map((tech) => (
                            <option key={tech.id} value={tech.id}>
                              {tech.full_name} · {tech.role || tech.team || 'Support'}
                            </option>
                          ))}
                        </select>
                      </label>

                      <button
                        type="button"
                        onClick={handleReassignTicket}
                        disabled={reassigning || !detailForm.assigned_to_id}
                        className="rounded-xl bg-autohall-blue px-4 py-2 text-sm font-semibold text-white hover:bg-autohall-darkBlue disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {reassigning ? 'Affectation...' : 'Enregistrer l’affectation'}
                      </button>
                      {emailSentAt && (
                        <div className="mt-1 text-sm text-green-700 dark:text-green-300">
                          E-mail envoyé au technicien · {new Date(emailSentAt).toLocaleTimeString('fr-FR')}
                        </div>
                      )}
                    </div>}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-2">
                      <PriorityBadge value={detailForm.priority} />
                      <CriticalityBadge value={detailForm.criticality} />
                    </div>
                    <button
                      onClick={handleSaveTicket}
                      disabled={detailLoading}
                      className="rounded-xl bg-autohall-blue px-4 py-2 text-sm font-semibold text-white hover:bg-autohall-darkBlue disabled:opacity-60"
                    >
                      Enregistrer
                    </button>
                  </div>

                  <div>
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">E-mail envoyé au technicien</div>
                    <div className="mt-2">
                      {emailDraftLoading && <div className="text-sm text-slate-500 dark:text-slate-400">Chargement du brouillon d'e-mail...</div>}
                      {emailDraftError && (
                        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
                          {emailDraftError}
                        </div>
                      )}
                      {!emailDraftLoading && !emailDraft && !emailDraftError && (
                        <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                          Aucun brouillon d'e-mail généré pour ce ticket.
                        </div>
                      )}
                      {emailDraft && <EmailDraft draft={emailDraft} />}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950/40">
                    <div className="text-sm font-semibold text-slate-900 dark:text-white">Ajouter un message</div>
                    <textarea
                      value={messageText}
                      onChange={(e) => setMessageText(e.target.value)}
                      rows={3}
                      placeholder="Réponse ou commentaire..."
                      className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                    />
                    <div className="mt-2 flex justify-end">
                      <button
                        onClick={handleAddMessage}
                        disabled={messageSaving}
                        className="rounded-xl bg-autohall-green px-4 py-2 text-sm font-semibold text-white hover:bg-green-600 disabled:opacity-60"
                      >
                        {messageSaving ? 'Envoi...' : 'Ajouter'}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <div className="text-sm font-semibold text-slate-900 dark:text-white">Messages</div>
                      <div className="mt-2 space-y-2">
                        {(detailForm.messages || []).length ? (
                          detailForm.messages.map((message) => (
                            <div key={message.id} className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950/40">
                              <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                                <span className="font-semibold uppercase tracking-[0.16em]">{message.sender_role}</span>
                                <span>{new Date(message.created_at).toLocaleString('fr-FR')}</span>
                              </div>
                              <div className="mt-1 text-sm text-slate-700 dark:text-slate-200">{message.content}</div>
                            </div>
                          ))
                        ) : (
                          <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                            Aucun message pour ce ticket.
                          </div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-sm font-semibold text-slate-900 dark:text-white">Historique</div>
                      <div className="mt-2 space-y-2">
                        {(detailForm.history || []).length ? (
                          detailForm.history.map((entry) => (
                            <div key={entry.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-800 dark:bg-slate-950/40">
                              <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                                <span className="font-semibold uppercase tracking-[0.16em]">{entry.field_name}</span>
                                <span>{new Date(entry.created_at).toLocaleString('fr-FR')}</span>
                              </div>
                              <div className="mt-1 text-slate-700 dark:text-slate-200">
                                <span className="font-medium">{entry.old_value || '—'}</span> <span className="text-slate-400">→</span> <span className="font-semibold">{entry.new_value || '—'}</span>
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                            Aucun historique.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
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