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

    const picker = document.createElement('div');
    picker.className = 'file-picker-shell';
    picker.setAttribute('role', 'group');
    picker.setAttribute('aria-live', 'polite');

    const selected = document.createElement('span');
    selected.className = 'file-picker-name';

    const actions = document.createElement('span');
    actions.className = 'file-picker-actions';

    const chooseBtn = document.createElement('button');
    chooseBtn.type = 'button';
    chooseBtn.className = 'file-picker-button';

    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'file-picker-clear';
    clearBtn.setAttribute('aria-label', t('Excluir arquivo'));
    clearBtn.textContent = '×';

    actions.appendChild(clearBtn);
    actions.appendChild(chooseBtn);
    picker.appendChild(selected);
    picker.appendChild(actions);
    input.insertAdjacentElement('afterend', picker);

    function update() {
      const name = fileLabel(input);
      const hasFile = Boolean(name);
      selected.textContent = hasFile ? name : t('Nenhum arquivo selecionado');
      chooseBtn.textContent = hasFile ? t('Selecionar outro') : t('Selecionar arquivo');
      clearBtn.setAttribute('aria-label', t('Excluir arquivo'));
      clearBtn.title = t('Excluir arquivo');
      clearBtn.hidden = !hasFile;
      picker.classList.toggle('has-file', hasFile);
    }

    chooseBtn.addEventListener('click', function () {
      input.click();
    });

    clearBtn.addEventListener('click', function () {
      input.value = '';
      input.dispatchEvent(new Event('change', { bubbles: true }));
      update();
    });

    picker.addEventListener('click', function (event) {
      if (event.target === picker || event.target === selected) input.click();
    });

    input.addEventListener('change', update);
    document.addEventListener('jt:language-change', update);
    window.addEventListener('jt-language-change', update);
    update();
  }

  function enhanceAll() {
    document.querySelectorAll('input[type="file"]').forEach(enhanceFileInput);
  }

  document.addEventListener('DOMContentLoaded', enhanceAll);
  window.addEventListener('load', enhanceAll);
  document.addEventListener('jt:language-change', enhanceAll);
  window.addEventListener('jt-language-change', enhanceAll);
  window.JT_FILE_INPUTS = { refresh: enhanceAll };
})();
