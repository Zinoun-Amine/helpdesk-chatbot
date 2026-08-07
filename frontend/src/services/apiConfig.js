const configuredApiUrl = (import.meta.env.VITE_API_URL || '').trim();

const browserApiUrl = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'http://localhost:8000';

export const API_BASE_URL = (configuredApiUrl || browserApiUrl).replace(/\/+$/, '');

export function apiError(error, url) {
  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return new Error(`Impossible de joindre l'API (${url}). Vérifiez que le backend est démarré et accessible.`);
  }
  return error;
}
