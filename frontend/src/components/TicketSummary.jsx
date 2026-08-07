import { CriticalityBadge, PriorityBadge } from './TicketBadges';

export default function TicketSummary({ ticket }) {

  return (
    <div className="my-4 p-4 rounded-xl border glass-panel shadow-sm w-full max-w-md animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-sm text-slate-500 dark:text-slate-400">
          Ticket #{ticket.id}
        </span>
        <div className="flex items-center gap-2"><PriorityBadge value={ticket.priority} /><CriticalityBadge value={ticket.criticality} /></div>
      </div>
      
      <h4 className="font-medium text-slate-800 dark:text-slate-100 mb-2 line-clamp-2">
        {ticket.title}
      </h4>
      
      <div className="space-y-2 mt-3 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-slate-400">Catégorie:</span>
          <span className="font-medium text-slate-700 dark:text-slate-200">{ticket.category}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-slate-400">Priorité:</span>
          <span className="font-medium text-slate-700 dark:text-slate-200">{ticket.priority}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-slate-400">Statut:</span>
          <span className="font-medium capitalize text-slate-700 dark:text-slate-200">{ticket.status}</span>
        </div>
      </div>
    </div>
  );
}
