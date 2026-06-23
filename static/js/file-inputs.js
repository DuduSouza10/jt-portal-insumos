(function () {
  function t(text) {
    return window.JT_I18N && typeof window.JT_I18N.t === 'function' ? window.JT_I18N.t(text) : text;
  }

  function fileLabel(input) {
    if (!input || !input.files || !input.files.length) return '';
    if (input.files.length === 1) return input.files[0].name;
    return input.files.length + ' ' + t('arquivos selecionados');
  }

  function enhanceFileInput(input) {
    if (!input || input.dataset.fileEnhanced === '1') return;
    input.dataset.fileEnhanced = '1';
    input.classList.add('enhanced-file-input');

    const panel = document.createElement('div');
    panel.className = 'file-input-control hidden';
    panel.setAttribute('aria-live', 'polite');

    const selected = document.createElement('span');
    selected.className = 'file-input-name';

    const actions = document.createElement('span');
    actions.className = 'file-input-actions';

    const changeBtn = document.createElement('button');
    changeBtn.type = 'button';
    changeBtn.className = 'btn tiny ghost file-change-btn';
    changeBtn.textContent = t('Selecionar outro');

    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'btn tiny ghost danger file-clear-btn';
    clearBtn.textContent = t('Excluir arquivo');

    actions.appendChild(changeBtn);
    actions.appendChild(clearBtn);
    panel.appendChild(selected);
    panel.appendChild(actions);
    input.insertAdjacentElement('afterend', panel);

    function update() {
      const name = fileLabel(input);
      if (name) {
        selected.textContent = t('Arquivo selecionado') + ': ' + name;
        panel.classList.remove('hidden');
      } else {
        selected.textContent = '';
        panel.classList.add('hidden');
      }
      changeBtn.textContent = t('Selecionar outro');
      clearBtn.textContent = t('Excluir arquivo');
    }

    changeBtn.addEventListener('click', function () {
      input.click();
    });

    clearBtn.addEventListener('click', function () {
      input.value = '';
      input.dispatchEvent(new Event('change', { bubbles: true }));
      update();
      input.focus({ preventScroll: true });
    });

    input.addEventListener('change', update);
    document.addEventListener('jt:language-change', update);
    update();
  }

  function enhanceAll() {
    document.querySelectorAll('input[type="file"]').forEach(enhanceFileInput);
  }

  document.addEventListener('DOMContentLoaded', enhanceAll);
  window.addEventListener('load', enhanceAll);
  document.addEventListener('jt:language-change', enhanceAll);
  window.JT_FILE_INPUTS = { refresh: enhanceAll };
})();
