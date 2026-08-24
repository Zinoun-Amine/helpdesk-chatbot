import { useState } from 'react';

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_PASSWORD_LENGTH = 6;

/**
 * Page d'inscription : nom complet + email + mot de passe (x2).
 *
 * Props :
 *  - onSignup(email, fullName, password)  : appelée à la soumission,
 *    doit throw pour afficher un message d'erreur.
 *  - onSwitchToLogin()                    : affichage du lien vers la
 *    page de connexion.
 */
export default function SignupPage({ onSignup, onSwitchToLogin }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();
    const trimmedPassword = password;

    if (!trimmedName || !trimmedEmail || !trimmedPassword) {
      setError('Veuillez remplir tous les champs.');
      return;
    }
    if (!EMAIL_REGEX.test(trimmedEmail)) {
      setError('Veuillez saisir une adresse email valide.');
      return;
    }
    if (trimmedPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`Le mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caractères.`);
      return;
    }
    if (trimmedPassword !== confirmPassword) {
      setError('Les deux mots de passe ne correspondent pas.');
      return;
    }

    try {
      setSubmitting(true);
      await onSignup(trimmedEmail, trimmedName, trimmedPassword);
    } catch (err) {
      setError(err?.message || 'Inscription impossible. Réessayez plus tard.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-autohall-bgLight px-4 py-12 text-autohall-textLight dark:bg-autohall-bgDark dark:text-autohall-textDark">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white/95 p-8 shadow-xl backdrop-blur dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mb-6 text-center">
          <img src="/autohall-logo.png" alt="AUTOHALL" className="mx-auto h-16 w-16 rounded-2xl" />
          <h1 className="mt-4 text-3xl font-bold text-slate-900 dark:text-white">Créer un compte</h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Inscrivez-vous pour utiliser le chatbot Helpdesk AUTOHALL.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit} noValidate>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Nom complet
            <input
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-autohall-blue focus:ring-2 focus:ring-autohall-blue/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              disabled={submitting}
            />
          </label>

          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Email professionnel
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-autohall-blue focus:ring-2 focus:ring-autohall-blue/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              disabled={submitting}
            />
          </label>

          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Mot de passe
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-autohall-blue focus:ring-2 focus:ring-autohall-blue/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              disabled={submitting}
            />
          </label>

          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
            Confirmer le mot de passe
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-autohall-blue focus:ring-2 focus:ring-autohall-blue/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              disabled={submitting}
            />
          </label>

          {error && (
            <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/40 dark:text-red-200">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-2xl bg-autohall-blue px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-autohall-darkBlue disabled:cursor-not-allowed disabled:opacity-70"
          >
            {submitting ? 'Création…' : 'Créer mon compte'}
          </button>
        </form>

        {onSwitchToLogin && (
          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Déjà un compte ?{' '}
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="font-semibold text-autohall-blue transition hover:text-autohall-darkBlue"
            >
              Se connecter
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
