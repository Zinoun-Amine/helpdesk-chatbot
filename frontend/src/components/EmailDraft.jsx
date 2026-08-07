import { useState } from 'react';
import * as api from '../services/api';

export default function EmailDraft({ draft }) {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    recipient: draft.recipient_email,
    subject: draft.subject,
    body: draft.body,
  });
  const [status, setStatus] = useState(draft.status); // 'draft' or 'sent'
  const [isSaving, setIsSaving] = useState(false);

  const isSent = status === 'sent';

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.updateEmailDraft(draft.id, formData);
      setIsEditing(false);
    } catch (err) {
      console.error(err);
      alert("Erreur lors de la sauvegarde.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSend = async () => {
    if (confirm("Êtes-vous sûr de vouloir envoyer cet e-mail ?")) {
      setIsSaving(true);
      try {
        await api.sendEmailDraft(draft.id);
        setStatus('sent');
      } catch (err) {
        console.error(err);
        alert("Erreur lors de l'envoi.");
      } finally {
        setIsSaving(false);
      }
    }
  };

  return (
    <div className="my-4 rounded-xl border glass-panel overflow-hidden w-full max-w-lg animate-fade-in shadow-md">
      {/* Header */}
      <div className="bg-slate-50 dark:bg-slate-800/50 p-3 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
        <div className="flex items-center space-x-2 text-slate-700 dark:text-slate-300 font-medium text-sm">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <span>E-mail généré</span>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${isSent ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400'}`}>
          {isSent ? 'Envoyé' : 'Brouillon'}
        </span>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">À :</label>
          {isEditing && !isSent ? (
            <input 
              type="email" name="recipient" value={formData.recipient} onChange={handleChange}
              className="w-full text-sm p-1.5 border rounded bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-autohall-blue"
            />
          ) : (
            <div className="text-sm text-slate-800 dark:text-slate-200">{formData.recipient}</div>
          )}
        </div>
        
        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Objet :</label>
          {isEditing && !isSent ? (
            <input 
              type="text" name="subject" value={formData.subject} onChange={handleChange}
              className="w-full text-sm p-1.5 border rounded bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-autohall-blue"
            />
          ) : (
            <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{formData.subject}</div>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Message :</label>
          {isEditing && !isSent ? (
            <textarea 
              name="body" value={formData.body} onChange={handleChange} rows={6}
              className="w-full text-sm p-2 border rounded bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-autohall-blue font-sans whitespace-pre-wrap"
            />
          ) : (
            <div className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap bg-slate-50 dark:bg-slate-800/30 p-3 rounded border border-slate-100 dark:border-slate-700/50">
              {formData.body}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      {!isSent && (
        <div className="p-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700 flex justify-end space-x-2">
          {isEditing ? (
            <>
              <button 
                onClick={() => setIsEditing(false)}
                className="px-3 py-1.5 text-sm rounded text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
              >
                Annuler
              </button>
              <button 
                onClick={handleSave} disabled={isSaving}
                className="px-3 py-1.5 text-sm rounded bg-autohall-blue text-white hover:bg-autohall-darkBlue transition disabled:opacity-50"
              >
                {isSaving ? 'Enregistrement...' : 'Enregistrer'}
              </button>
            </>
          ) : (
            <>
              <button 
                onClick={() => setIsEditing(true)}
                className="px-3 py-1.5 text-sm rounded border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
              >
                Modifier
              </button>
              <button 
                onClick={handleSend} disabled={isSaving}
                className="px-3 py-1.5 text-sm rounded bg-autohall-green text-white hover:bg-green-600 transition flex items-center space-x-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
                <span>Envoyer l'e-mail</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
