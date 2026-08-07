import { useEffect, useState } from 'react';

const defaultDraft = {
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

export default function TicketDraftModal({ isOpen, initialValues, isSaving, error, onClose, onSubmit }) {
  const [form, setForm] = useState(defaultDraft);

  useEffect(() => {
    if (isOpen) {
      setForm({
        ...defaultDraft,
        ...initialValues,
      });
    }
  }, [initialValues, isOpen]);

  if (!isOpen) return null;

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit(form);
  };

  return (
    <div className="pointer-events-none fixed inset-0 z-[60] flex items-start justify-end p-3 sm:p-5">
      <div className="pointer-events-auto max-h-[calc(100vh-6rem)] w-full max-w-xl overflow-y-auto rounded-2xl border border-slate-200/70 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 sm:px-5">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Préparer le ticket</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Vérifiez les suggestions avant création.</p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200" aria-label="Fermer">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-3 p-4 sm:gap-4 sm:p-5 md:grid-cols-2">
          <label className="space-y-2 md:col-span-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Titre</span>
            <input name="title" value={form.title} onChange={handleChange} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none ring-0 focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Catégorie</span>
            <input name="category" value={form.category} onChange={handleChange} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Priorité</span>
            <select name="priority" value={form.priority} onChange={handleChange} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Urgent</option>
            </select>
          </label>

          <label className="space-y-2 md:col-span-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Résumé</span>
            <textarea name="summary" value={form.summary} onChange={handleChange} rows={2} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>

          <label className="space-y-2 md:col-span-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Description</span>
            <textarea name="description" value={form.description} onChange={handleChange} rows={3} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Nom utilisateur</span>
            <input name="user_name" value={form.user_name} onChange={handleChange} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>

          <label className="space-y-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Email utilisateur</span>
            <input name="user_email" type="email" value={form.user_email} onChange={handleChange} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none focus:border-autohall-blue dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
          </label>

          <div className="md:col-span-2 flex flex-col gap-3 pt-2">
            {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">{error}</div>}
            <div className="flex items-center justify-end gap-3">
              <button type="button" onClick={onClose} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">Annuler</button>
              <button type="submit" disabled={isSaving} className="rounded-lg bg-autohall-blue px-4 py-2 text-sm font-semibold text-white hover:bg-autohall-darkBlue disabled:cursor-not-allowed disabled:opacity-70">
                {isSaving ? 'Création...' : 'Créer le ticket'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
