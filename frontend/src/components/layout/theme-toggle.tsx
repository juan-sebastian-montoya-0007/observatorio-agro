'use client';

import { useSyncExternalStore } from 'react';
import { Moon, Sun } from 'lucide-react';

function subscribe(callback: () => void) {
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  return () => observer.disconnect();
}
export function useDarkTheme() {
  return useSyncExternalStore(subscribe, () => document.documentElement.dataset.theme === 'dark', () => false);
}
export function ThemeToggle() {
  const dark = useDarkTheme();
  function toggle() {
    const theme = dark ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('agro-theme', theme); } catch { /* Storage can be disabled. */ }
  }
  return <button type="button" className="theme-toggle" onClick={toggle} aria-pressed={dark} aria-label="Modo oscuro">
    {dark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    <span>{dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}</span>
  </button>;
}
