import { useState } from 'react';
import * as api from '../services/api';

export default function TicketStatus() {
  const [ticketId, setTicketId] = useState('');
  const [statusData, setStatusData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!ticketId) return;

    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getTicketStatus(ticketId);
      setStatusData(data);
    } catch (err) {
      setError("Ticket introuvable ou erreur de connexion.");
      setStatusData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const steps = [
    { id: 'nouveau', label: 'Nouveau' },
    { id: 'en_cours', label: 'En cours' },
    { id: 'resolu', label: 'Résolu' },
    { id: 'clos', label: 'Clos' }
  ];

  const getStepIndex = (status) => steps.findIndex(s => s.id === status);

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden flex flex-col h-full max-h-[600px]">
      <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
        <h3 className="font-semibold text-slate-800 dark:text-slate-200 flex items-center space-x-2">
          <svg className="w-5 h-5 text-autohall-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <span>Suivi de ticket</span>
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Consultez l'état d'avancement d'un ticket existant</p>
      </div>

      <div className="p-4 flex-1 overflow-y-auto">
        <form onSubmit={handleSearch} className="flex space-x-2 mb-6">
          <input
            type="number"
            value={ticketId}
            onChange={(e) => setTicketId(e.target.value)}
            placeholder="N° du ticket..."
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-autohall-blue focus:border-transparent outline-none transition"
            required
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 bg-autohall-blue text-white text-sm font-medium rounded-lg hover:bg-autohall-darkBlue transition disabled:opacity-70"
          >
            {isLoading ? '...' : 'Chercher'}
          </button>
        </form>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm rounded-lg border border-red-200 dark:border-red-800 mb-4 animate-fade-in">
            {error}
          </div>
        )}

        {statusData && (
          <div className="animate-slide-up space-y-6">
            <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-lg border border-slate-200 dark:border-slate-700">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Ticket #{statusData.id}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusData.type === 1 ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400'}`}>
                  {statusData.type === 1 ? 'Incident' : 'Demande'}
                </span>
              </div>
              <h4 className="font-medium text-slate-800 dark:text-slate-200 line-clamp-2 mb-3">{statusData.title}</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <p className="text-slate-500 dark:text-slate-400 text-xs">Catégorie</p>
                  <p className="font-medium text-slate-700 dark:text-slate-300">{statusData.category}</p>
                </div>
                <div>
                  <p className="text-slate-500 dark:text-slate-400 text-xs">Priorité</p>
                  <p className="font-medium text-slate-700 dark:text-slate-300">P{statusData.priority} - {statusData.criticality}</p>
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className="relative">
              <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-200 dark:bg-slate-700"></div>
              <div className="space-y-6 relative">
                {steps.map((step, idx) => {
                  const currentIndex = getStepIndex(statusData.status);
                  const isCompleted = idx < currentIndex;
                  const isCurrent = idx === currentIndex;
                  
                  return (
                    <div key={step.id} className="flex items-center space-x-4">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center relative z-10 border-2 ${
                        isCompleted ? 'bg-autohall-green border-autohall-green text-white' :
                        isCurrent ? 'bg-white dark:bg-slate-800 border-autohall-blue text-autohall-blue' :
                        'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-600'
                      }`}>
                        {isCompleted && <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"/></svg>}
                        {isCurrent && <div className="w-2 h-2 rounded-full bg-autohall-blue animate-pulse"></div>}
                      </div>
                      <div className={`text-sm font-medium ${isCurrent || isCompleted ? 'text-slate-800 dark:text-slate-200' : 'text-slate-400 dark:text-slate-500'}`}>
                        {step.label}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
