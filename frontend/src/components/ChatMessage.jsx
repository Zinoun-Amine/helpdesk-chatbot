import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import TicketSummary from './TicketSummary';
import EmailDraft from './EmailDraft';

export default function ChatMessage({ message, isStreaming = false, onFeedback, onRewrite }) {
  const isUser = message.role === 'user';
  const [feedback, setFeedback] = useState(message.feedback || null);

  const handleFeedback = async (rating) => {
    if (feedback || !onFeedback) return;
    try {
      await onFeedback(message.id, rating);
      setFeedback(rating);
    } catch (error) {
      console.error('Feedback impossible à enregistrer:', error);
    }
  };
  
  return (
    <div className={`flex w-full my-6 animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="relative mr-3 flex h-8 w-12 flex-shrink-0 items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-white shadow-md dark:border-slate-700 dark:bg-slate-900">
          <img
            src="/autohall-logo.png"
            alt="Assistant Auto Hall"
            className="h-full w-full object-cover object-center [filter:contrast(1.2)_brightness(1.45)]"
          />
          <span className="absolute bottom-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-green-500 ring-1 ring-white dark:ring-slate-900" />
        </div>
      )}
      
      <div className={`max-w-[85%] md:max-w-[75%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div 
          className={`px-5 py-3.5 rounded-2xl shadow-sm text-[15px] leading-relaxed ${
            isUser 
              ? 'rounded-2xl bg-autohall-blue text-white shadow-md' 
              : 'rounded-2xl border border-slate-200 bg-white text-slate-800 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200'
          }`}
        >
          {isUser ? (
            <>
              <div className="whitespace-pre-wrap">{message.content}</div>
              {message.attachments?.length > 0 && (
                <div className="mt-3 space-y-1 border-t border-white/20 pt-2 text-xs text-blue-100">
                  {message.attachments.map(attachment => <div key={attachment.id || attachment.name}>📎 {attachment.name}</div>)}
                </div>
              )}
            </>
          ) : (
            <div className="markdown-body font-sans">
              {message.content ? (
                <>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                  {isStreaming && <span className="ml-1 inline-block h-4 w-1 animate-typing-caret rounded-full bg-autohall-blue align-middle" aria-label="Réponse en cours" />}
                </>
              ) : (
                <div className="flex space-x-1 items-center h-5">
                  <div className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse-dot"></div>
                  <div className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse-dot animation-delay-200"></div>
                  <div className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse-dot animation-delay-400"></div>
                </div>
              )}
            </div>
          )}
        </div>

        {!isUser && message.content && !isStreaming && (onFeedback || onRewrite) && (
          <div className="mt-2 flex items-center gap-1 text-xs text-slate-400" aria-label="Évaluer la réponse">
            <span className="mr-1">Cette réponse vous aide ?</span>
            {onFeedback && <>
              <button type="button" onClick={() => handleFeedback(1)} className={`rounded-lg px-2 py-1 transition hover:bg-green-50 hover:text-green-700 dark:hover:bg-green-900/30 ${feedback === 1 ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : ''}`} aria-label="Réponse utile">👍</button>
              <button type="button" onClick={() => handleFeedback(-1)} className={`rounded-lg px-2 py-1 transition hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/30 ${feedback === -1 ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' : ''}`} aria-label="Réponse inutile">👎</button>
            </>}
            {onRewrite && <>
              <span className="mx-1 h-4 w-px bg-slate-200 dark:bg-slate-700" />
              <button type="button" onClick={() => onRewrite('Reformule ta dernière réponse de manière plus courte, avec uniquement les étapes essentielles.')} className="rounded-lg px-2 py-1 transition hover:bg-blue-50 hover:text-blue-700 dark:hover:bg-blue-900/30">Plus court</button>
              <button type="button" onClick={() => onRewrite('Reformule ta dernière réponse avec plus de détails et des étapes numérotées.')} className="rounded-lg px-2 py-1 transition hover:bg-blue-50 hover:text-blue-700 dark:hover:bg-blue-900/30">Plus détaillé</button>
            </>}
          </div>
        )}
        
        {/* Render Actions (Tickets, Emails) */}
        {message.actions && message.actions.map((action, idx) => {
          if (action.action === 'ticket_created' && action.ticket) {
            return <TicketSummary key={`action-${idx}`} ticket={action.ticket} />;
          }
          if (action.action === 'email_draft' && action.draft) {
            return <EmailDraft key={`action-${idx}`} draft={action.draft} />;
          }
          if (action.action === 'kb_result') {
            return (
              <div key={`action-${idx}`} className="my-3 inline-flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-1 text-[10px] font-medium text-green-700 dark:border-green-900/50 dark:bg-green-900/20 dark:text-green-300">
                <span>Base de connaissances consultée</span>
                <span>({(action.results || []).length} résultat{(action.results || []).length > 1 ? 's' : ''})</span>
              </div>
            );
          }
          return null;
        })}
        
        <span className="mt-1.5 px-1 text-[10px] text-slate-500 dark:text-slate-400">
          {new Date(message.timestamp || message.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {message.responseTimeMs ? ` · Réponse en ${(message.responseTimeMs / 1000).toFixed(1)} s` : ''}
        </span>
      </div>
    </div>
  );
}
