import { API_BASE_URL, apiError } from './apiConfig';

const TOKEN_KEY = 'autohall-token';

/**
 * Récupère le JWT stocké (synchronisé avec ce qu'écrit `useAuth`).
 * Lecture défensive : en cas d'erreur d'accès localStorage, retourne null.
 */
export function getStoredToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

async function requestJSON(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (error) {
    throw apiError(error, url);
  }
  if (!res.ok) {
    const message = await res.text().catch(() => '');
    throw new Error(message || `HTTP ${res.status} — ${url}`);
  }
  return res.json();
}

function authHeaders(extra = {}) {
  const token = getStoredToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

/**
 * Connexion : POST /auth/login
 * Retour : { access_token, token_type, user }
 */
export async function login({ email, password }) {
  return requestJSON(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ email, password }),
  });
}

/**
 * Inscription : POST /auth/register
 * Retour : { access_token, token_type, user }
 */
export async function signup({ email, full_name, password }) {
  return requestJSON(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ email, full_name, password }),
  });
}

/**
 * Profil courant : GET /auth/me
 * Utilise le token déjà stocké.
 */
export async function fetchCurrentUser() {
  return requestJSON(`${API_BASE_URL}/auth/me`, {
    headers: authHeaders(),
  });
}
