import { useState, useEffect } from 'react';

export function useTheme() {
  const [themeMode, setThemeMode] = useState(() => localStorage.getItem('theme') || 'system');

  const getSystemPreference = () => window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDarkMode = themeMode === 'dark' || (themeMode === 'system' && getSystemPreference());

  const updateThemeMode = (nextMode) => {
    setThemeMode(nextMode);
    localStorage.setItem('theme', nextMode);
    window.dispatchEvent(new Event('themechange'));
  };

  useEffect(() => {
    const root = window.document.documentElement;
    if (isDarkMode) {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  }, [isDarkMode, themeMode]);

  useEffect(() => {
    const syncTheme = () => setThemeMode(localStorage.getItem('theme') || 'system');
    window.addEventListener('storage', syncTheme);
    window.addEventListener('themechange', syncTheme);
    return () => {
      window.removeEventListener('storage', syncTheme);
      window.removeEventListener('themechange', syncTheme);
    };
  }, []);

  const toggleTheme = () => updateThemeMode(themeMode === 'dark' ? 'light' : 'dark');

  return { isDarkMode, themeMode, setThemeMode: updateThemeMode, toggleTheme };
}
