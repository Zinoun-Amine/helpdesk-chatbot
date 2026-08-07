import { useEffect, useRef, useState } from 'react';

const SUGGESTIONS = [
  { label: 'VPN inaccessible', text: 'Je n’arrive pas à me connecter au VPN depuis mon poste.' },
  { label: 'Mot de passe Messagerie', text: 'Ma messagerie me redemande mon mot de passe en boucle.' },
  { label: 'Wincar indisponible', text: 'Wincar ne s’ouvre pas et affiche un message d’erreur.' },
  { label: 'Imprimante bloquée', text: 'L’imprimante de mon agence ne répond plus.' },
  { label: 'Demande d’installation', text: 'Je souhaite demander l’installation d’un logiciel.' },
];

export default function ChatInput({ onSendMessage, isStreaming }) {
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const [value, setValue] = useState('');
  const [files, setFiles] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [fileError, setFileError] = useState(null);

  useEffect(() => {
    if (!isStreaming && inputRef.current) inputRef.current.focus();
  }, [isStreaming]);

  const handleKeyDown = (event) => {
    if (event.key === 'Escape') setShowSuggestions(false);
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (isStreaming || !value.trim()) return;
    onSendMessage(value.trim(), files);
    setValue('');
    setFiles([]);
    setFileError(null);
    setShowSuggestions(false);
    if (inputRef.current) inputRef.current.style.height = 'auto';
  };

  const handleInput = (event) => {
    const nextValue = event.target.value;
    setValue(nextValue);
    setShowSuggestions(Boolean(nextValue.trim()));
    event.target.style.height = 'auto';
    event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`;
  };

  const handleFileChange = (event) => {
    const selected = Array.from(event.target.files || []);
    const tooLarge = selected.find(file => file.size > 10 * 1024 * 1024);
    if (tooLarge) {
      setFileError('Chaque fichier doit faire 10 Mo maximum.');
      return;
    }
    setFileError(null);
    setFiles(previous => [...previous, ...selected].slice(0, 5));
    event.target.value = '';
  };

  const filteredSuggestions = SUGGESTIONS
    .filter(item => item.text.toLowerCase().includes(value.toLowerCase()))
    .slice(0, 3);

  return (
    <div className="relative">
      {showSuggestions && value.trim() && !isStreaming && filteredSuggestions.length > 0 && (
        <div className="absolute bottom-[calc(100%+0.35rem)] left-2 z-30 w-64 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg dark:border-slate-700 dark:bg-slate-900">
          <div className="px-2 pb-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Suggestions</div>
          {filteredSuggestions.map(item => (
            <button
              key={item.label}
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                setValue(item.text);
                setShowSuggestions(false);
                inputRef.current?.focus();
              }}
              className="flex w-full items-center rounded-lg px-2 py-1.5 text-left text-xs text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <span className="mr-2 h-1.5 w-1.5 rounded-full bg-autohall-blue" />
              {item.label}
            </button>
          ))}
        </div>
      )}

      {files.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {files.map((file, index) => (
            <span key={`${file.name}-${index}`} className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">
              <span className="max-w-[180px] truncate">{file.name}</span>
              <button type="button" onClick={() => setFiles(previous => previous.filter((_, fileIndex) => fileIndex !== index))} aria-label={`Retirer ${file.name}`}>×</button>
            </span>
          ))}
        </div>
      )}
      {fileError && <p className="mb-2 text-xs text-red-600 dark:text-red-400">{fileError}</p>}

      <div className="relative flex items-end rounded-2xl border border-slate-300 bg-white p-2 shadow-lg transition-all dark:border-slate-700 dark:bg-slate-900">
        <textarea
          ref={inputRef}
          rows={1}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          placeholder={isStreaming ? 'Le chatbot répond...' : 'Décrivez votre problème...'}
          className="flex-1 max-h-[120px] resize-none bg-transparent px-4 py-3 text-slate-900 outline-none placeholder:text-slate-400 scrollbar-custom dark:text-slate-100 dark:placeholder:text-slate-500"
          style={{ minHeight: '48px' }}
        />
        <input ref={fileInputRef} type="file" multiple className="hidden" accept=".png,.jpg,.jpeg,.webp,.pdf,.txt,.csv,.log,.doc,.docx,.xls,.xlsx,.zip" onChange={handleFileChange} />
        <button type="button" onClick={() => fileInputRef.current?.click()} disabled={isStreaming || files.length >= 5} className="m-1 rounded-xl p-3 text-slate-500 transition hover:bg-slate-100 hover:text-autohall-blue disabled:opacity-40 dark:text-slate-400 dark:hover:bg-slate-800" aria-label="Ajouter une pièce jointe" title="Ajouter une capture, un log ou un document">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.586-6.586a4 4 0 00-5.656-5.656l-6.586 6.586a6 6 0 108.485 8.485L20 13" /></svg>
        </button>
        <button type="button" onClick={handleSend} disabled={isStreaming || !value.trim()} className={`m-1 flex items-center justify-center rounded-xl p-3 transition-all ${isStreaming || !value.trim() ? 'cursor-not-allowed bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-500' : 'bg-autohall-blue text-white hover:bg-autohall-darkBlue hover:shadow-md hover:scale-105 active:scale-95'}`} aria-label="Envoyer le message">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
        </button>
      </div>
    </div>
  );
}
