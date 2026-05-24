/**
 * SerpentAI 主题切换模块
 * 支持浅色/深色/自动三种模式
 * 使用 localStorage 持久化用户偏好
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'serpent-theme';
  const MODES = ['light', 'dark', 'auto'];

  function getSystemPreference() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function getStoredMode() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'auto';
    } catch {
      return 'auto';
    }
  }

  function getEffectiveTheme(mode) {
    return mode === 'auto' ? getSystemPreference() : mode;
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    // Update meta theme-color for mobile browsers
    let meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.name = 'theme-color';
      document.head.appendChild(meta);
    }
    meta.content = theme === 'dark' ? '#1a1a2e' : '#ffffff';
  }

  function init() {
    const mode = getStoredMode();
    const theme = getEffectiveTheme(mode);
    applyTheme(theme);

    // Listen for system preference changes
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    if (mql.addEventListener) {
      mql.addEventListener('change', () => {
        if (getStoredMode() === 'auto') {
          applyTheme(getSystemPreference());
        }
      });
    } else if (mql.addListener) {
      mql.addListener(() => {
        if (getStoredMode() === 'auto') {
          applyTheme(getSystemPreference());
        }
      });
    }

    // Expose global API
    window.SerpentTheme = {
      /** Set theme mode: 'light' | 'dark' | 'auto' */
      setMode(newMode) {
        if (!MODES.includes(newMode)) {
          console.warn('Invalid theme mode:', newMode);
          return;
        }
        try {
          localStorage.setItem(STORAGE_KEY, newMode);
        } catch { /* ignore */ }
        applyTheme(getEffectiveTheme(newMode));
        dispatchEvent(new CustomEvent('themechange', {
          detail: { mode: newMode, theme: getEffectiveTheme(newMode) }
        }));
      },

      /** Get current mode */
      getMode() {
        return getStoredMode();
      },

      /** Get effective applied theme */
      getTheme() {
        return getEffectiveTheme(getStoredMode());
      },

      /** Cycle through modes: light -> dark -> auto -> light */
      cycle() {
        const modes = MODES;
        const current = getStoredMode();
        const next = modes[(modes.indexOf(current) + 1) % modes.length];
        this.setMode(next);
        return next;
      },

      /** Available modes */
      MODES: MODES,
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
