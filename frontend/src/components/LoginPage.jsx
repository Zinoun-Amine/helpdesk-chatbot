import { useState } from 'react';

export default function LoginPage({ onLogin }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    setError(null);

    if (!name.trim() || !email.trim()) {
      setError('Veuillez renseigner votre nom et votre email.');
      return;
    }

    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setError('Veuillez saisir une adresse email valide.');
      return;
    }

    onLogin({ name: name.trim(), email: email.trim() });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-autohall-bgLight px-4 py-12 text-autohall-textLight dark:bg-autohall-bgDark dark:text-autohall-textDark">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white/95 p-8 shadow-xl backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mb-6 text-center">
          <img src="/autohall-logo.png" alt="AUTOHALL" className="mx-auto h-16 w-16 rounded-2xl" />
          <h1 className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">Connexion</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Entrez vos informations pour accéder au chatbot Helpdesk.</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Nom complet
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-autohall-blue focus:ring-2 focus:ring-autohall-blue/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
          </label>

          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Email professionnel
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-autohall-blue focus:ring-2 focus:ring-autohall-blue/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
          </label>

          {error && <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-200">{error}</p>}

          <button
            type="submit"
            className="w-full rounded-2xl bg-autohall-blue px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-autohall-darkBlue"
          >
            Se connecter
          </button>
        </form>
      </div>
    </div>
  );
}
