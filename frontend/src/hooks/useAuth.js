import { useCallback, useState } from 'react';
import * as authApi from '../services/authApi.js';

const TOKEN_KEY = 'autohall-token';
const USER_KEY = 'autohall-user';

/**
 * Lit le token + le profil utilisateur persistés dans localStorage.
 * Retourne `{ token, user }` si les deux sont présents, sinon `null`.
 * Toute erreur d'accès au localStorage est silencieusement ignorée
 * (sessions privées, navigation privée, etc.).
 */
function readStoredAuth() {
  try {
    const token = window.localStorage.getItem(TOKEN_KEY);
    const userRaw = window.localStorage.getItem(USER_KEY);
    if (!token || !userRaw) return null;
    const user = JSON.parse(userRaw);
    if (!user || typeof user !== 'object') return null;
    return { token, user };
  } catch {
    return null;
  }
}

function persistAuth(token, user) {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // Stockage indisponible : la session marchera jusqu'au reload.
  }
}

function clearStoredAuth() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Hook d'authentification centralisé.
 * Expose : `{ user, token, isAuthenticated, login, signup, logout }`.
 */
export function useAuth() {
  const [auth, setAuth] = useState(() => readStoredAuth());

  const handleAuthSuccess = useCallback((response) => {
    const { access_token, user } = response;
    persistAuth(access_token, user);
    setAuth({ token: access_token, user });
    return user;
  }, []);

  const login = useCallback(
    async (email, password) => {
      const response = await authApi.login({ email, password });
      return handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const signup = useCallback(
    async (email, fullName, password) => {
      const response = await authApi.signup({
        email,
        full_name: fullName,
        password,
      });
      return handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const logout = useCallback(() => {
    clearStoredAuth();
    setAuth(null);
  }, []);

  return {
    user: auth?.user || null,
    token: auth?.token || null,
    isAuthenticated: !!auth,
    login,
    signup,
    logout,
  };
}
