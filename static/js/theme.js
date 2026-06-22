(function () {
  const STORAGE_KEY = 'jt-insumos-theme';
  const root = document.documentElement;
  const savedTheme = localStorage.getItem(STORAGE_KEY);
  const preferredLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
  const initialTheme = savedTheme || (preferredLight ? 'light' : 'dark');

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    const logo = document.getElementById('brandLogoTheme');
    if (logo) {
      const nextSrc = theme === 'light' ? logo.dataset.lightSrc : logo.dataset.darkSrc;
      if (nextSrc && logo.getAttribute('src') !== nextSrc) {
        logo.setAttribute('src', nextSrc);
      }
    }
    const button = document.getElementById('themeToggle');
    if (button) {
      button.setAttribute('aria-pressed', String(theme === 'light'));
      button.title = theme === 'light' ? 'Mudar para tema escuro' : 'Mudar para tema claro';
    }
  }

  applyTheme(initialTheme);

  window.addEventListener('DOMContentLoaded', function () {
    const button = document.getElementById('themeToggle');
    if (!button) return;
    button.addEventListener('click', function () {
      const nextTheme = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      applyTheme(nextTheme);
    });
  });
})();
