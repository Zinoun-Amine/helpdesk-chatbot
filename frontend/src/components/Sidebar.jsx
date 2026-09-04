import ThemeToggle from './ThemeToggle';

const navigationItems = [
  { id: 'chat', label: 'Chat', icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z' },
  { id: 'tickets', label: 'Tickets', icon: 'M9 12h6m-6 4h6M10 3h4a2 2 0 012 2v2H8V5a2 2 0 012-2zM6 7h12a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V9a2 2 0 012-2z' },
  { id: 'dashboard', label: 'Dashboard', icon: 'M4 6h7v7H4V6zm9 11h7v3h-7v-3zm0-11h7v8h-7V6zM4 15h7v5H4v-5z' },
  { id: 'settings', label: 'Settings', icon: 'M12 8.25a3.75 3.75 0 100 7.5 3.75 3.75 0 000-7.5zM19.4 15a7.97 7.97 0 00.1-1 7.97 7.97 0 00-.1-1l2.03-1.58a.5.5 0 00.12-.65l-1.92-3.32a.5.5 0 00-.61-.22l-2.39.96a8.24 8.24 0 00-1.73-1l-.36-2.54a.5.5 0 00-.5-.43h-3.84a.5.5 0 00-.5.43l-.36 2.54c-.62.25-1.2.59-1.73 1l-2.39-.96a.5.5 0 00-.61.22L2.45 10.77a.5.5 0 00.12.65L4.6 13a7.97 7.97 0 000 2l-2.03 1.58a.5.5 0 00-.12.65l1.92 3.32a.5.5 0 00.61.22l2.39-.96c.53.41 1.11.75 1.73 1l.36 2.54a.5.5 0 00.5.43h3.84a.5.5 0 00.5-.43l.36-2.54c.62-.25 1.2-.59 1.73-1l2.39.96a.5.5 0 00.61-.22l1.92-3.32a.5.5 0 00-.12-.65L19.4 15z' },
];

export default function Sidebar({ onNewChat, onNavigate, activeView, isOpen, toggleSidebar, isCollapsed = false, onToggleCollapse, role = 'user' }) {
  const visibleItems = navigationItems.filter(item => (
    role === 'admin' || (role === 'technician' && item.id === 'tickets') || (role === 'user' && item.id === 'chat')
  ));
  const canStartChat = role !== 'technician';
  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm md:hidden animate-fade-in" onClick={toggleSidebar}></div>
      )}

      <aside className={`fixed md:static inset-y-0 left-0 z-50 w-72 ${isCollapsed ? 'md:w-20' : 'md:w-72'} bg-white/95 backdrop-blur-xl border-r border-slate-200 dark:bg-slate-900/95 dark:border-slate-800 flex flex-col transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className={`p-5 border-b border-slate-200 dark:border-slate-800 flex items-center ${isCollapsed ? 'justify-between md:justify-center' : 'justify-between'}`}>
          <div className="flex items-center space-x-3">
            <div className={`h-10 w-28 shrink-0 overflow-hidden rounded-lg bg-white shadow-md ring-1 ring-slate-200 dark:ring-slate-700 ${isCollapsed ? 'md:w-10' : ''}`}>
              <img src="/autohall-logo.png" alt="Auto Hall" className="h-full w-full object-cover object-center [filter:contrast(1.2)_brightness(1.45)]" />
            </div>
            <div className={isCollapsed ? 'md:hidden' : ''}>
              <h1 className="font-bold text-slate-800 dark:text-white text-[14px] leading-tight">Helpdesk IT</h1>
              <p className="text-[9px] text-slate-500 dark:text-slate-400 font-medium tracking-[0.12em] uppercase">Support AUTOHALL</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button onClick={onToggleCollapse} className="hidden rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 md:inline-flex" aria-label={isCollapsed ? 'Développer la navigation' : 'Réduire la navigation'} title={isCollapsed ? 'Développer' : 'Réduire'}>
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={isCollapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'} /></svg>
            </button>
            <div className="md:hidden">
              <button onClick={toggleSidebar} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800" aria-label="Fermer la navigation">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </div>
        </div>

        <div className="p-4 space-y-2">
          {canStartChat && <button onClick={() => { onNewChat(); if (window.innerWidth < 768) toggleSidebar(); }} className={`w-full flex items-center ${isCollapsed ? 'md:justify-center' : 'space-x-2'} rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700`}>
            <svg className="w-5 h-5 text-autohall-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            <span className={isCollapsed ? 'md:hidden' : ''}>Nouvelle demande</span>
          </button>}

          <div className="space-y-1 pt-2">
            {visibleItems.map(item => (
              <button key={item.id} onClick={() => { onNavigate(item.id); if (window.innerWidth < 768) toggleSidebar(); }} className={`w-full flex items-center ${isCollapsed ? 'md:justify-center' : 'space-x-3'} px-4 py-3 rounded-xl border transition-colors text-left ${activeView === item.id ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/50 dark:bg-blue-900/20 dark:text-blue-300' : 'border-transparent bg-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.icon} /></svg>
                <span className={`font-medium ${isCollapsed ? 'md:hidden' : ''}`}>{item.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className={`flex-1 overflow-y-auto p-4 ${isCollapsed ? 'md:hidden' : ''}`}>
          <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Informations</h3>
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 dark:border-blue-900/50 dark:bg-blue-900/20">
            <p className="text-[13px] leading-relaxed text-slate-700 dark:text-slate-200">Ce chatbot utilise l'intelligence artificielle pour diagnostiquer votre problème et vous proposer des solutions rapides ou créer un ticket pour nos techniciens.</p>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-800/50">
          <div className={`flex items-center space-x-3 ${isCollapsed ? 'md:hidden' : ''}`}>
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
              <svg className="h-4 w-4 text-slate-500 dark:text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Utilisateur</span>
              <span className="flex items-center text-[10px] font-medium text-green-600 dark:text-green-400"><span className="mr-1 h-1.5 w-1.5 rounded-full bg-green-500"></span> Connecté</span>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}
