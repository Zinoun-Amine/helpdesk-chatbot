import { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import QualificationProgress from './QualificationProgress';

export default function ChatWindow({ messages, isStreaming, onSendMessage, qualification, onFeedback }) {
  const endOfMessagesRef = useRef(null);

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-inner dark:border-slate-800 dark:bg-slate-950/50">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 scrollbar-custom">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 animate-fade-in">
            <div className="relative mb-6 flex h-16 w-20 items-center justify-center overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
              <img src="/autohall-logo.png" alt="Auto Hall" className="h-full w-full object-cover object-center [filter:contrast(1.2)_brightness(1.45)]" />
              <span className="absolute bottom-1.5 right-1.5 h-2 w-2 rounded-full bg-green-500 ring-2 ring-white dark:ring-slate-900" />
            </div>
            <h2 className="mb-2 text-2xl font-bold text-slate-900 dark:text-white">Comment puis-je vous aider ?</h2>
            <p className="mx-auto max-w-sm text-sm text-slate-500 dark:text-slate-400">
              Décrivez votre problème technique (Internet, imprimante, Wincar, etc.) ou demandez un nouveau service.
            </p>
          </div>
        ) : (
          <div className="space-y-2 pb-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} isStreaming={isStreaming && msg.role === 'assistant' && msg === messages[messages.length - 1]} onFeedback={onFeedback} onRewrite={onSendMessage} />
            ))}
            <div ref={endOfMessagesRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="relative z-20 border-t border-slate-200 bg-white/85 p-3 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/85 md:p-5">
        <div className="max-w-4xl mx-auto">
          <QualificationProgress qualification={qualification} />
          <ChatInput onSendMessage={onSendMessage} isStreaming={isStreaming} />
          <div className="text-center mt-3">
            <p className="text-[10px] text-slate-500 dark:text-slate-400">
              Assistant IA AUTOHALL — Peut commettre des erreurs. Considérez vérifier les informations importantes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
