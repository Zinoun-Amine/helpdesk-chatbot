import { useEffect, useState } from 'react';
import * as api from '../services/api';
import { useTheme } from '../hooks/useTheme';

const defaultSettings = {
  general: { chatbot_name: 'AUTOHALL Helpdesk', language: 'fr' },
  appearance: { theme: 'system' },
  chat: { temperature: 0.3, max_tokens: 2048, streaming: true, memory: true, history: true, sources: true },
  llm: { primary_provider: 'ollama', fallback_1: 'groq', fallback_2: 'gemini', enable_fallback: true },
  notifications: { tickets: true, status_changes: true, errors: true, system_events: true },
  providers: [],
};

function Section({ title, description, children }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
      </div>
      {children}
    </section>
  );
}

export default function SettingsPage() {
  const { themeMode, setThemeMode } = useTheme();
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [providerResults, setProviderResults] = useState({});

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await api.getSettings();
        if (!ignore) setSettings({ ...defaultSettings, ...payload });
      } catch (err) {
        if (!ignore) setError(err.message || 'Impossible de charger les paramètres.');
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    load();
    return () => { ignore = true; };
  }, []);

  const updateNested = (section, key, value) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...(prev[section] || {}),
        [key]: value,
      },
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      const payload = {
        general: settings.general,
        appearance: settings.appearance,
        chat: settings.chat,
        llm: settings.llm,
        notifications: settings.notifications,
      };
      const saved = await api.saveSettings(payload);
      setSettings(prev => ({ ...prev, ...saved }));
      setThemeMode(settings.appearance.theme || 'system');
    } catch (err) {
      setError(err.message || 'Impossible d’enregistrer les paramètres.');
    } finally {
      setSaving(false);
    }
  };

  const handleProviderTest = async (provider) => {
    setProviderResults(prev => ({ ...prev, [provider]: { loading: true } }));
    try {
      const result = await api.testProviderConnection(provider);
      setProviderResults(prev => ({ ...prev, [provider]: result }));
    } catch (err) {
      setProviderResults(prev => ({ ...prev, [provider]: { ok: false, message: err.message || 'Erreur', loading: false } }));
    }
  };

  const providerStatusByName = Object.fromEntries((settings.providers || []).map(provider => [provider.name, provider]));

  return (
    <div className="space-y-6 p-2 md:p-4">
      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="text-xs font-semibold uppercase tracking-[0.2em] text-autohall-blue">Settings</div>
        <h2 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Configuration de l’application</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">Les réglages sont stockés dans la base de données et les providers restent gérés par les variables d’environnement sécurisées.</p>
      </div>

      {error && <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-2">
        <Section title="General" description="Nom, langue et paramètres généraux du chatbot.">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Nom du chatbot</span>
              <input value={settings.general.chatbot_name || ''} onChange={(e) => updateNested('general', 'chatbot_name', e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Langue</span>
              <select value={settings.general.language || 'fr'} onChange={(e) => updateNested('general', 'language', e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                <option value="fr">Français</option>
                <option value="en">English</option>
                <option value="ar">العربية</option>
              </select>
            </label>
          </div>
        </Section>

        <Section title="Appearance" description="Réutilise le système de thème existant.">
          <div className="grid grid-cols-3 gap-3">
            {['light', 'dark', 'system'].map((mode) => (
              <button key={mode} onClick={() => { updateNested('appearance', 'theme', mode); setThemeMode(mode); }} className={`rounded-2xl border px-4 py-4 text-sm font-semibold transition ${settings.appearance.theme === mode || themeMode === mode ? 'border-autohall-blue bg-autohall-blue/10 text-autohall-darkBlue dark:text-autohall-blue' : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-200'}`}>
                {mode === 'light' ? 'Light Mode' : mode === 'dark' ? 'Dark Mode' : 'System Mode'}
              </button>
            ))}
          </div>
        </Section>

        <Section title="Chat Settings" description="Options prises en charge par le projet actuel.">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Température</span>
              <input type="number" step="0.1" min="0" max="1" value={settings.chat.temperature ?? 0.3} onChange={(e) => updateNested('chat', 'temperature', Number(e.target.value))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Max tokens</span>
              <input type="number" min="256" step="128" value={settings.chat.max_tokens ?? 2048} onChange={(e) => updateNested('chat', 'max_tokens', Number(e.target.value))} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100" />
            </label>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {[
              ['streaming', 'Streaming'],
              ['memory', 'Mémoire'],
              ['sources', 'Affichage des sources'],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm dark:bg-slate-800/50">
                <span className="font-medium text-slate-700 dark:text-slate-200">{label}</span>
                <input type="checkbox" checked={Boolean(settings.chat[key])} onChange={(e) => updateNested('chat', key, e.target.checked)} className="h-5 w-5 rounded border-slate-300 text-autohall-blue focus:ring-autohall-blue" />
              </label>
            ))}
          </div>
        </Section>

        <Section title="LLM Providers" description="Priorité: Ollama → Groq → Gemini. Les secrets restent côté backend/env.">
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Primary Provider</span>
                <select value={settings.llm.primary_provider || 'ollama'} onChange={(e) => updateNested('llm', 'primary_provider', e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                  <option value="ollama">Ollama</option>
                  <option value="groq">Groq</option>
                  <option value="gemini">Gemini</option>
                </select>
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Fallback 1</span>
                <select value={settings.llm.fallback_1 || 'groq'} onChange={(e) => updateNested('llm', 'fallback_1', e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                  <option value="groq">Groq</option>
                  <option value="gemini">Gemini</option>
                  <option value="ollama">Ollama</option>
                </select>
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Fallback 2</span>
                <select value={settings.llm.fallback_2 || 'gemini'} onChange={(e) => updateNested('llm', 'fallback_2', e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                  <option value="gemini">Gemini</option>
                  <option value="groq">Groq</option>
                  <option value="ollama">Ollama</option>
                </select>
              </label>
            </div>

            <label className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm dark:bg-slate-800/50">
              <span className="font-medium text-slate-700 dark:text-slate-200">Activer le fallback</span>
              <input type="checkbox" checked={Boolean(settings.llm.enable_fallback)} onChange={(e) => updateNested('llm', 'enable_fallback', e.target.checked)} className="h-5 w-5 rounded border-slate-300 text-autohall-blue focus:ring-autohall-blue" />
            </label>

            <div className="grid gap-3 md:grid-cols-3">
              {(settings.providers || []).map((provider) => {
                const testResult = providerResults[provider.name];
                return (
                  <div key={provider.name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">{provider.label}</div>
                        <div className="mt-1 text-base font-bold text-slate-900 dark:text-white">{provider.status}</div>
                      </div>
                      <div className="h-3 w-3 rounded-full bg-autohall-green" />
                    </div>
                    <div className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                      {provider.primary ? 'Provider principal' : provider.fallback ? 'Fallback configuré' : 'Disponible'}
                    </div>
                    <button onClick={() => handleProviderTest(provider.name)} className="mt-4 w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">Test Connection</button>
                    {testResult && !testResult.loading && (
                      <div className={`mt-3 rounded-xl px-3 py-2 text-xs ${testResult.ok ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' : 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300'}`}>
                        {testResult.message}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </Section>

        <Section title="Notifications" description="Activez ou désactivez les notifications système et métier.">
          <div className="grid gap-3 md:grid-cols-2">
            {[
              ['tickets', 'Tickets'],
              ['status_changes', 'Changements de statut'],
              ['errors', 'Erreurs'],
              ['system_events', 'Événements système'],
            ].map(([key, label]) => (
              <label key={key} className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm dark:bg-slate-800/50">
                <span className="font-medium text-slate-700 dark:text-slate-200">{label}</span>
                <input type="checkbox" checked={Boolean(settings.notifications[key])} onChange={(e) => updateNested('notifications', key, e.target.checked)} className="h-5 w-5 rounded border-slate-300 text-autohall-blue focus:ring-autohall-blue" />
              </label>
            ))}
          </div>
        </Section>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} disabled={loading || saving} className="rounded-xl bg-autohall-blue px-6 py-3 text-sm font-semibold text-white hover:bg-autohall-darkBlue disabled:cursor-not-allowed disabled:opacity-70">
          {saving ? 'Enregistrement...' : 'Enregistrer les paramètres'}
        </button>
      </div>
    </div>
  );
}
