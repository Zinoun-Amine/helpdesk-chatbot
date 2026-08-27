import { createContext, useCallback, useContext, useState } from 'react';
import * as authApi from '../services/authApi.js';

const TOKEN_KEY = 'autohall-token';
const USER_KEY = 'autohall-user';

const AuthContext = createContext(null);

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
    // The session remains available until a page reload if storage is unavailable.
  }
}

function clearStoredAuth() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    // Ignore storage errors during logout.
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => readStoredAuth());

  const handleAuthSuccess = useCallback((response) => {
    const { access_token: token, user } = response;
    persistAuth(token, user);
    setAuth({ token, user });
    return user;
  }, []);

  const login = useCallback(async (email, password) => {
    const response = await authApi.login({ email, password });
    return handleAuthSuccess(response);
  }, [handleAuthSuccess]);

  const signup = useCallback(async (email, fullName, password) => {
    const response = await authApi.signup({
      email,
      full_name: fullName,
      password,
    });
    return handleAuthSuccess(response);
  }, [handleAuthSuccess]);

  const logout = useCallback(() => {
    clearStoredAuth();
    setAuth(null);
  }, []);

  const value = {
    user: auth?.user || null,
    token: auth?.token || null,
    isAuthenticated: Boolean(auth),
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used inside an AuthProvider');
  }
  return context;
}
