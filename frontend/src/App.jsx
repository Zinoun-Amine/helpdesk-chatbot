import React, { useEffect, useMemo, useState } from 'react';
import ChatWindow from './components/ChatWindow';
import Sidebar from './components/Sidebar';
import ThemeToggle from './components/ThemeToggle';
import TicketsPage from './components/TicketsPage';
import DashboardPage from './components/DashboardPage';
import SettingsPage from './components/SettingsPage';
import TicketDraftModal from './components/TicketDraftModal';
import LoginPage from './components/LoginPage';
import SignupPage from './components/SignupPage';
import { useChat } from './hooks/useChat';
import { useTheme } from './hooks/useTheme';
import { useAuth } from './hooks/useAuth';
import { AuthProvider } from './contexts/AuthContext.jsx';
import * as api from './services/api';

function AppContent() {
  const { themeMode, toggleTheme } = useTheme();
  const { user, login, signup, logout } = useAuth();
  const [activeView, setActiveView] = useState(() => user?.role === 'technician' ? 'tickets' : 'chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try { return window.localStorage.getItem('autohall-sidebar-collapsed') === 'true'; } catch { return false; }
  });
  const [draftModalOpen, setDraftModalOpen] = useState(false);
  const [draftInitialValues, setDraftInitialValues] = useState(null);
  const [draftSaving, setDraftSaving] = useState(false);
  const [draftError, setDraftError] = useState(null);
  // Vue d'auth affichée quand il n'y a pas d'utilisateur connecté.
  // 'login' = page de connexion, 'signup' = page d'inscription.
  const [authView, setAuthView] = useState('login');
  const {
    messages,
    sendMessage,
    isStreaming,
    clearChat,
    conversationId,
    qualification,
    rateMessage,
  } = useChat(user);

  useEffect(() => {
    if (user?.role === 'technician') setActiveView('tickets');
    else if (user?.role === 'user') setActiveView('chat');
  }, [user]);

  const viewLabels = useMemo(() => ({
    chat: 'Chat',
    tickets: 'Tickets',
    dashboard: 'Dashboard',
    settings: 'Settings',
  }), []);

  const handleNavigate = (view) => {
    if (user.role === 'technician' && view !== 'tickets') return;
    if (user.role === 'user' && view !== 'chat') return;
    if (user.role !== 'admin' && view === 'dashboard') return;
    if (user.role !== 'admin' && view === 'settings') return;
    setActiveView(view);
    setSidebarOpen(false);
  };

  const handleNewChat = () => {
    clearChat();
    setActiveView('chat');
    setSidebarOpen(false);
  };

  /**
   * Appelé par LoginPage. Doit throw pour afficher un message d'erreur.
   * Après succès, l'utilisateur est persisté via `useAuth.login`.
   */
  const handleLogin = async (email, password) => {
    const loggedUser = await login(email, password);
    setActiveView(loggedUser?.role === 'technician' ? 'tickets' : 'chat');
  };

  /**
   * Appelé par SignupPage. Doit throw pour afficher un message d'erreur.
   * Après succès, l'utilisateur est persisté via `useAuth.signup`.
   */
  const handleSignup = async (email, fullName, password) => {
    await signup(email, fullName, password);
    setActiveView('chat');
  };

  const handleLogout = () => {
    logout();
    setAuthView('login');
    clearChat();
  };

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed(previous => {
      const next = !previous;
      try { window.localStorage.setItem('autohall-sidebar-collapsed', String(next)); } catch { /* stockage indisponible */ }
      return next;
    });
  };

  const openTicketDraftFromConversation = async () => {
    try {
      setDraftSaving(true);
      setDraftError(null);
      const payload = {
        messages: messages.map(message => ({ role: message.role, content: message.content })),
        conversation_id: conversationId,
        user_name: user?.full_name || 'Utilisateur AUTOHALL',
        user_email: user?.email || 'employe.fictif@autohall.ma',
      };
      const suggestion = await api.draftTicketFromConversation(payload);
      setDraftInitialValues({
        ...suggestion,
        status: 'Open',
        ticket_type: 1,
        conversation_id: conversationId,
        user_name: user?.full_name || 'Utilisateur AUTOHALL',
        user_email: user?.email || 'employe.fictif@autohall.ma',
      });
      setDraftModalOpen(true);
    } catch (err) {
      setDraftError(err.message || 'Impossible de générer le ticket.');
      setDraftModalOpen(true);
    } finally {
      setDraftSaving(false);
    }
  };

  const handleDraftSubmit = async (form) => {
    try {
      setDraftSaving(true);
      setDraftError(null);
      await api.createTicket({
        ...form,
        conversation_id: conversationId ?? form.conversation_id ?? null,
        ticket_type: form.ticket_type || 1,
      });
      setDraftModalOpen(false);
      setDraftInitialValues(null);
      setActiveView('tickets');
    } catch (err) {
      setDraftError(err.message || 'Impossible de créer le ticket.');
    } finally {
      setDraftSaving(false);
    }
  };


  if (!user) {
    return authView === 'signup' ? (
      <SignupPage
        onSignup={handleSignup}
        onSwitchToLogin={() => setAuthView('login')}
      />
    ) : (
      <LoginPage
        onLogin={handleLogin}
        onSwitchToSignup={() => setAuthView('signup')}
      />
    );
  }

  return (
    <div className="flex h-screen bg-autohall-bgLight text-autohall-textLight transition-colors duration-300 font-sans dark:bg-autohall-bgDark dark:text-autohall-textDark">
      <Sidebar
        onNewChat={handleNewChat}
        onNavigate={handleNavigate}
        activeView={activeView}
        isOpen={sidebarOpen}
        toggleSidebar={() => setSidebarOpen(prev => !prev)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapsed}
        role={user.role}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur flex items-center justify-between px-6 z-20 dark:border-slate-800 dark:bg-slate-900/80">
          <div className="flex items-center gap-3">
            <button className="rounded-xl border border-slate-200 p-2 text-slate-700 dark:border-slate-700 dark:text-slate-200 md:hidden" onClick={() => setSidebarOpen(prev => !prev)} aria-label="Ouvrir la navigation">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
            </button>
            <div>
              <h1 className="font-bold text-xl text-slate-900 dark:text-white">Helpdesk IT AUTOHALL</h1>
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{viewLabels[activeView]}</p>
            </div>
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-blue-700 dark:border-blue-900/50 dark:bg-blue-900/20 dark:text-blue-300"><span className="h-1.5 w-1.5 rounded-full bg-blue-500" />Bêta</span>
          </div>
          <div className="flex items-center gap-3">
            {user.role !== 'technician' && activeView === 'chat' && messages.length > 0 && (
              <button
                onClick={openTicketDraftFromConversation}
                disabled={draftSaving || isStreaming}
                className="max-w-[9rem] truncate rounded-lg bg-autohall-blue px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-autohall-darkBlue disabled:cursor-not-allowed disabled:opacity-70 sm:max-w-none sm:px-3 sm:py-2"
              >
                <span className="sm:hidden">Ticket</span>
                <span className="hidden sm:inline">Transformer en ticket</span>
              </button>
            )}
            <div className="hidden sm:flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
              <div>
                <div className="font-semibold">{user.full_name}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{user.email}</div>
              </div>
              <button onClick={handleLogout} className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700">Déconnexion</button>
            </div>
            <ThemeToggle themeMode={themeMode} toggleTheme={toggleTheme} />
          </div>
        </header>

        <main className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
          {user.role !== 'technician' && activeView === 'chat' && (
            <div key="chat" className="flex-1 p-2 md:p-4 overflow-hidden animate-page-enter">
              <ChatWindow
                messages={messages}
                isStreaming={isStreaming}
                onSendMessage={sendMessage}
                qualification={qualification}
                onFeedback={rateMessage}
              />
            </div>
          )}

          {activeView === 'tickets' && <div key="tickets" className="flex-1 min-h-0 overflow-y-auto animate-page-enter"><TicketsPage /></div>}
          {user.role === 'admin' && activeView === 'dashboard' && <div key="dashboard" className="flex-1 min-h-0 overflow-y-auto animate-page-enter"><DashboardPage /></div>}
          {user.role === 'admin' && activeView === 'settings' && <div key="settings" className="flex-1 min-h-0 overflow-y-auto animate-page-enter"><SettingsPage /></div>}
        </main>
      </div>

      <TicketDraftModal
        isOpen={draftModalOpen}
        initialValues={draftInitialValues}
        isSaving={draftSaving}
        error={draftError}
        onClose={() => {
          setDraftModalOpen(false);
          setDraftInitialValues(null);
          setDraftError(null);
        }}
        onSubmit={handleDraftSubmit}
      />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
