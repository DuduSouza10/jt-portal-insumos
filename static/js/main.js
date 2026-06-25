const productGrid = document.getElementById('productGrid');
const productSearch = document.getElementById('productSearch');
const refreshProducts = document.getElementById('refreshProducts');
const categoryFilter = document.getElementById('categoryFilter');
const productSort = document.getElementById('productSort');
const productResultCount = document.getElementById('productResultCount');
const productViewButtons = Array.from(document.querySelectorAll('[data-product-view]'));
const emptyState = document.getElementById('emptyState');
const cartItems = document.getElementById('cartItems');
const cartCount = document.getElementById('cartCount');
const clearCart = document.getElementById('clearCart');
const submitRequest = document.getElementById('submitRequest');
const cartMessage = document.getElementById('cartMessage');
const requestNote = document.getElementById('requestNote');
const requestPeopleCount = document.getElementById('requestPeopleCount');
const downloadLastPdf = document.getElementById('downloadLastPdf');

let products = [];
let cart = new Map();
let debounceTimer = null;
let productView = 'grid';

try {
  productView = window.localStorage.getItem('jt-product-view') === 'list' ? 'list' : 'grid';
} catch (error) {
  productView = 'grid';
}

function jtText(text) {
  return window.JT_I18N && typeof window.JT_I18N.t === 'function' ? window.JT_I18N.t(text) : text;
}

function setMessage(text, type = '') {
  cartMessage.textContent = text || '';
  cartMessage.className = `cart-message ${type}`;
}

function hideLastPdfButton() {
  if (!downloadLastPdf) return;
  downloadLastPdf.classList.add('hidden');
  downloadLastPdf.href = '#';
}

function showLastPdfButton(requestId) {
  if (!downloadLastPdf || !requestId) return;
  downloadLastPdf.href = `/solicitacoes/${requestId}/pdf`;
  downloadLastPdf.classList.remove('hidden');
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function isKitProduct(product) {
  return !!(product && product.is_kit && Number(product.kit_quantity || 0) > 1);
}

function kitMultiplier(product) {
  return isKitProduct(product) ? Math.max(1, Number(product.kit_quantity || 1)) : 1;
}

function toRequestUnits(product, quantity) {
  const numeric = Math.max(0, Number(quantity || 0));
  return numeric * kitMultiplier(product);
}

function kitUnitText(product) {
  const unitLabel = jtText(product.unit_measure || 'un');
  return `${kitMultiplier(product)} ${unitLabel}`;
}

async function loadProducts() {
  const q = productSearch.value.trim();
  const category = categoryFilter ? categoryFilter.value : '';
  const sort = productSort ? productSort.value : 'name';
  productGrid.innerHTML = `<div class="card empty-state">${jtText('Carregando insumos...')}</div>`;
  emptyState.classList.add('hidden');
  const params = new URLSearchParams({ q, category, sort });
  try {
    const response = await fetch(`/api/products?${params.toString()}`);
    products = await response.json();
    renderProducts();
  } catch (error) {
    products = [];
    renderProducts();
    setMessage(jtText('Não foi possível carregar os insumos.'), 'err');
  }
}

function applyProductView() {
  productGrid.classList.toggle('view-list', productView === 'list');
  productGrid.classList.toggle('view-grid', productView === 'grid');
  productViewButtons.forEach((button) => {
    const active = button.dataset.productView === productView;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
}

function bindAddProduct(container, product) {
  const qtyInput = container.querySelector('[data-product-quantity]');
  const button = container.querySelector('[data-add-product]');
  if (!qtyInput || !button) return;

  const productName = jtText(product.name || '');
  const minimum = Number(product.min_order_quantity || 1);
  button.addEventListener('click', () => {
    const quantity = parseInt(qtyInput.value, 10);
    if (!quantity || quantity <= 0) {
      setMessage(jtText('Informe uma quantidade válida.'), 'err');
      return;
    }
    const current = cart.get(product.id)?.quantity || 0;
    const requestedQuantity = current + quantity;
    const requestedUnits = toRequestUnits(product, requestedQuantity);
    if (requestedUnits < minimum) {
      setMessage(jtText(`A quantidade mínima para ${productName} é ${minimum}.`), 'err');
      return;
    }
    if (product.limit !== null && product.limit !== undefined && requestedUnits > product.limit) {
      setMessage(jtText(`Limite de insumos excedido para ${productName}. Limite permitido: ${product.limit}.`), 'err');
      return;
    }
    cart.set(product.id, { product, quantity: requestedQuantity });
    renderCart();
    setMessage(jtText(`${productName} adicionado à solicitação.`), 'ok');
  });
}

function renderProductCards() {
  products.forEach((product, index) => {
    const card = document.createElement('article');
    card.className = 'product-card card';
    card.style.animationDelay = `${Math.min(index * 0.045, 0.45)}s`;

    const unit = product.unit_measure || 'un';
    const unitLabel = jtText(unit);
    const productName = jtText(product.name || '');
    const productCategory = jtText(product.category || '');
    const productDescription = product.description ? jtText(product.description) : jtText('Sem descrição cadastrada.');
    const priceBadge = product.show_price ? `<span class="badge red">${escapeHtml(product.price)} / ${escapeHtml(unitLabel)}</span>` : '';
    const unitBadge = `<span class="badge">${jtText('Unidade')}: ${escapeHtml(unitLabel)}</span>`;
    const kitBadge = isKitProduct(product) ? `<span class="badge">${jtText('Kit')}: ${escapeHtml(kitUnitText(product))}</span>` : '';
    const stockBadge = product.show_stock ? `<span class="badge">${jtText('Estoque')}: ${product.stock_quantity} ${escapeHtml(unitLabel)}</span>` : '';
    const limitBadge = product.limit !== null && product.limit !== undefined ? `<span class="badge">${jtText('Limite')}: ${product.limit} ${escapeHtml(unitLabel)}</span>` : `<span class="badge">${jtText('Sem limite definido')}</span>`;
    const minimum = Number(product.min_order_quantity || 1);
    const inputMinimum = isKitProduct(product) ? 1 : minimum;
    const minimumBadge = minimum > 1 ? `<span class="badge minimum-badge">${jtText('Pedido mínimo')}: ${minimum} ${escapeHtml(unitLabel)}</span>` : '';
    const categoryEmoji = escapeHtml(product.category_emoji || '📦');
    const imageButton = product.image_url ? `
      <button
        class="product-thumb-button"
        type="button"
        data-image-preview="${escapeHtml(product.image_url)}"
        data-image-title="${escapeHtml(productName)}"
        title="${escapeHtml(jtText('Ampliar imagem'))}"
      >
        <img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(productName)}">
      </button>
    ` : '';

    card.innerHTML = `
      <div class="product-card-content">
        <div class="product-head">
          <span class="product-head-assets">
            <span class="product-icon" aria-hidden="true">${categoryEmoji}</span>
            ${imageButton}
          </span>
          <span class="product-category">${escapeHtml(productCategory)}</span>
        </div>
        <div class="product-copy">
          <h3>${escapeHtml(productName)}</h3>
          <p>${escapeHtml(productDescription)}</p>
        </div>
        <div class="meta-row">
          ${priceBadge}
          ${unitBadge}
          ${kitBadge}
          ${stockBadge}
          ${limitBadge}
          ${minimumBadge}
        </div>
      </div>
      <div class="add-row">
        <input data-product-quantity type="number" min="${inputMinimum}" value="${inputMinimum}" aria-label="${jtText(isKitProduct(product) ? 'Quantidade de kits' : 'Quantidade')}">
        <button data-add-product class="btn primary" type="button">${jtText('Adicionar')}</button>
      </div>
    `;
    bindAddProduct(card, product);
    productGrid.appendChild(card);
  });
}

function renderProductTable() {
  const wrapper = document.createElement('div');
  wrapper.className = 'request-products-table-wrap card';
  const rows = products.map((product) => {
    const unit = product.unit_measure || 'un';
    const unitLabel = jtText(unit);
    const productName = jtText(product.name || '');
    const productCategory = jtText(product.category || 'Sem categoria');
    const productDescription = product.description ? jtText(product.description) : jtText('Sem descrição cadastrada.');
    const minimum = Number(product.min_order_quantity || 1);
    const inputMinimum = isKitProduct(product) ? 1 : minimum;
    const kitText = isKitProduct(product) ? `${jtText('Kit')}: ${kitUnitText(product)}` : '-';
    const price = product.show_price
      ? `<strong>${escapeHtml(product.price)}</strong><small>/ ${escapeHtml(unitLabel)}</small>`
      : `<span class="muted">${jtText('Oculto')}</span>`;
    const stock = product.show_stock
      ? `<strong>${product.stock_quantity}</strong><small>${escapeHtml(unitLabel)}</small>`
      : `<span class="muted">${jtText('Oculto')}</span>`;
    const limit = product.limit !== null && product.limit !== undefined
      ? `${product.limit} ${escapeHtml(unitLabel)}`
      : jtText('Sem limite');
    const minimumOrder = minimum > 1 ? `${minimum} ${escapeHtml(unitLabel)}` : '-';
    const imageButton = product.image_url ? `
      <button
        class="product-thumb-button"
        type="button"
        data-image-preview="${escapeHtml(product.image_url)}"
        data-image-title="${escapeHtml(productName)}"
        title="${escapeHtml(jtText('Ampliar imagem'))}"
      >
        <img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(productName)}">
      </button>
    ` : '';

    return `
      <tr data-request-product-row data-product-id="${product.id}">
        <td data-label="${escapeHtml(jtText('Produto'))}">
          <div class="request-product-main ${product.image_url ? 'has-image' : ''}">
            <span class="request-product-icon" aria-hidden="true">${escapeHtml(product.category_emoji || '📦')}</span>
            ${imageButton}
            <div>
              <strong>${escapeHtml(productName)}</strong>
              <small>${escapeHtml(productDescription)}</small>
            </div>
          </div>
        </td>
        <td data-label="${escapeHtml(jtText('Categoria'))}">
          <strong>${escapeHtml(productCategory)}</strong>
        </td>
        <td class="request-product-value" data-label="${escapeHtml(jtText('Preço / unidade'))}">${price}</td>
        <td class="request-product-value" data-label="${escapeHtml(jtText('Estoque'))}">${stock}</td>
        <td data-label="${escapeHtml(jtText('Regras do pedido'))}">
          <div class="request-product-rules">
            <span><b>${jtText('Limite')}:</b> ${limit}</span>
            <span><b>${jtText('Pedido mínimo')}:</b> ${minimumOrder}</span>
            <span><b>${jtText('Kit')}:</b> ${escapeHtml(kitText)}</span>
          </div>
        </td>
        <td class="request-product-quantity" data-label="${escapeHtml(jtText('Quantidade'))}">
          <input data-product-quantity type="number" min="${inputMinimum}" value="${inputMinimum}" aria-label="${escapeHtml(jtText(isKitProduct(product) ? 'Quantidade de kits' : 'Quantidade'))}">
        </td>
        <td class="request-product-action" data-label="${escapeHtml(jtText('Ação'))}">
          <button data-add-product class="btn primary" type="button">${jtText('Adicionar')}</button>
        </td>
      </tr>
    `;
  }).join('');

  wrapper.innerHTML = `
    <table class="request-products-table">
      <thead>
        <tr>
          <th>${jtText('Produto')}</th>
          <th>${jtText('Categoria')}</th>
          <th>${jtText('Preço / unidade')}</th>
          <th>${jtText('Estoque')}</th>
          <th>${jtText('Regras do pedido')}</th>
          <th>${jtText('Quantidade')}</th>
          <th>${jtText('Ação')}</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;

  wrapper.querySelectorAll('[data-request-product-row]').forEach((row) => {
    const productId = Number(row.dataset.productId);
    const product = products.find((item) => Number(item.id) === productId);
    if (product) bindAddProduct(row, product);
  });
  productGrid.appendChild(wrapper);
}

function renderProducts() {
  productGrid.innerHTML = '';
  if (productResultCount) productResultCount.textContent = String(products.length);
  applyProductView();
  if (!products.length) {
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');
  if (productView === 'list') {
    renderProductTable();
  } else {
    renderProductCards();
  }
}

function renderCart() {
  cartItems.innerHTML = '';
  const values = Array.from(cart.values());
  const totalQty = values.reduce((sum, item) => sum + toRequestUnits(item.product, item.quantity), 0);
  cartCount.textContent = `${totalQty} ${totalQty === 1 ? jtText('item') : jtText('itens')}`;

  if (!values.length) {
    cartItems.innerHTML = `<div class="muted center">${jtText('Sua lista está vazia.')}</div>`;
    return;
  }

  values.forEach((item, index) => {
    const div = document.createElement('div');
    div.className = 'cart-item';
    div.style.animationDelay = `${Math.min(index * 0.035, 0.25)}s`;
    const minimum = Number(item.product.min_order_quantity || 1);
    const inputMinimum = isKitProduct(item.product) ? 1 : minimum;
    const unitLabel = jtText(item.product.unit_measure || 'un');
    const requestedUnits = toRequestUnits(item.product, item.quantity);
    const minimumText = minimum > 1 ? ` • ${jtText('Mínimo')}: ${minimum} ${unitLabel}` : '';
    const kitText = isKitProduct(item.product) ? ` • ${item.quantity} ${jtText('kits')} = ${requestedUnits} ${unitLabel}` : '';
    div.innerHTML = `
      <div>
        <strong>${escapeHtml(jtText(item.product.name || ''))}</strong>
        <span>${item.product.show_price ? escapeHtml(item.product.price) : jtText('Valor oculto')} / ${escapeHtml(unitLabel)}${minimumText}${escapeHtml(kitText)}</span>
      </div>
      <input type="number" min="${inputMinimum}" value="${item.quantity}" aria-label="${escapeHtml(jtText(isKitProduct(item.product) ? 'Quantidade de kits' : 'Quantidade'))}">
      <button class="btn ghost danger" type="button">×</button>
    `;
    const input = div.querySelector('input');
    const remove = div.querySelector('button');
    input.addEventListener('change', () => {
      const quantity = parseInt(input.value, 10);
      if (!quantity || quantity <= 0) {
        input.value = item.quantity;
        return;
      }
      const requestedUnits = toRequestUnits(item.product, quantity);
      if (requestedUnits < minimum) {
        input.value = item.quantity;
        setMessage(jtText(`A quantidade mínima para ${jtText(item.product.name || '')} é ${minimum}.`), 'err');
        return;
      }
      if (item.product.limit !== null && item.product.limit !== undefined && requestedUnits > item.product.limit) {
        input.value = item.quantity;
        setMessage(jtText(`Limite de insumos excedido para ${jtText(item.product.name || '')}. Limite permitido: ${item.product.limit}.`), 'err');
        return;
      }
      cart.set(item.product.id, { product: item.product, quantity });
      renderCart();
    });
    remove.addEventListener('click', () => {
      cart.delete(item.product.id);
      renderCart();
      setMessage(jtText('Item removido.'), '');
    });
    cartItems.appendChild(div);
  });
}

async function sendRequest() {
  hideLastPdfButton();
  const values = Array.from(cart.values());
  if (!values.length) {
    setMessage(jtText('Adicione pelo menos um insumo antes de enviar.'), 'err');
    return;
  }
  let peopleCount = null;
  if (requestPeopleCount) {
    peopleCount = parseInt(requestPeopleCount.value, 10);
    if (!peopleCount || peopleCount <= 0 || peopleCount > 99999) {
      setMessage(jtText('Informe o número de pessoas na base.'), 'err');
      requestPeopleCount.focus();
      return;
    }
  }
  submitRequest.disabled = true;
  setMessage(jtText('Enviando solicitação...'), '');
  try {
    const response = await fetch('/api/requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: values.map(item => ({ product_id: item.product.id, quantity: item.quantity })),
        people_count: peopleCount,
        user_note: requestNote.value.trim()
      })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      setMessage(jtText(data.message || 'Não foi possível enviar a solicitação.'), 'err');
      return;
    }
    cart.clear();
    requestNote.value = '';
    if (requestPeopleCount) requestPeopleCount.value = '';
    renderCart();
    setMessage(jtText(`Solicitação #${data.request_id} enviada para aprovação. PDF disponível para download.`), 'ok');
    showLastPdfButton(data.request_id);
  } catch (error) {
    setMessage(jtText('Erro de conexão ao enviar solicitação.'), 'err');
  } finally {
    submitRequest.disabled = false;
  }
}

productSearch.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadProducts, 250);
});
if (categoryFilter) categoryFilter.addEventListener('change', loadProducts);
if (productSort) productSort.addEventListener('change', loadProducts);
productViewButtons.forEach((button) => {
  button.addEventListener('click', () => {
    productView = button.dataset.productView === 'list' ? 'list' : 'grid';
    try {
      window.localStorage.setItem('jt-product-view', productView);
    } catch (error) {
      // A visualização continua funcionando mesmo se o navegador bloquear o armazenamento local.
    }
    renderProducts();
  });
});
refreshProducts.addEventListener('click', loadProducts);
clearCart.addEventListener('click', () => {
  cart.clear();
  renderCart();
  hideLastPdfButton();
  setMessage(jtText('Lista limpa.'), '');
});
submitRequest.addEventListener('click', sendRequest);

renderCart();
loadProducts();


window.addEventListener('jt-language-change', function () {
  if (Array.isArray(products)) renderProducts();
  renderCart();
});

// v63 - formulários com base/franquia separados em relatórios
(function () {
  function setupSeparatedUnitForms() {
    document.querySelectorAll('[data-unit-required-form], [data-separated-unit-form]').forEach(function (form) {
      if (form.dataset.unitFormReady === '1') return;
      form.dataset.unitFormReady = '1';
      const baseSelect = form.querySelector('[data-report-base-select], [data-base-select]');
      const franchiseSelect = form.querySelector('[data-report-franchise-select], [data-franchise-select]');
      const allUnitsToggle = form.querySelector('[data-report-all-units]');
      function sync(changed) {
        if (!baseSelect || !franchiseSelect) return;
        if (allUnitsToggle && allUnitsToggle.checked) {
          baseSelect.value = '';
          franchiseSelect.value = '';
          baseSelect.disabled = true;
          franchiseSelect.disabled = true;
          return;
        }
        if (baseSelect) baseSelect.disabled = false;
        if (franchiseSelect) franchiseSelect.disabled = false;
        if (changed === baseSelect && baseSelect.value) franchiseSelect.value = '';
        if (changed === franchiseSelect && franchiseSelect.value) baseSelect.value = '';
      }
      if (allUnitsToggle) {
        allUnitsToggle.addEventListener('change', function () { sync(allUnitsToggle); });
        sync(allUnitsToggle);
      }
      if (baseSelect) baseSelect.addEventListener('change', function () { sync(baseSelect); });
      if (franchiseSelect) franchiseSelect.addEventListener('change', function () { sync(franchiseSelect); });
      if (form.hasAttribute('data-unit-required-form')) {
        form.addEventListener('submit', function (event) {
          const allSelected = !!(allUnitsToggle && allUnitsToggle.checked);
          const hasBase = !!(baseSelect && baseSelect.value);
          const hasFranchise = !!(franchiseSelect && franchiseSelect.value);
          if (allSelected) return;
          if (hasBase && hasFranchise) {
            event.preventDefault();
            alert(window.jtText ? window.jtText('Selecione somente uma base ou uma franquia, não as duas.') : 'Selecione somente uma base ou uma franquia, não as duas.');
            return;
          }
          if (!hasBase && !hasFranchise) {
            event.preventDefault();
            alert(window.jtText ? window.jtText('Selecione uma base, uma franquia ou marque “Selecionar todos” para gerar o relatório completo.') : 'Selecione uma base, uma franquia ou marque “Selecionar todos” para gerar o relatório completo.');
          }
        });
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupSeparatedUnitForms);
  } else {
    setupSeparatedUnitForms();
  }
  window.addEventListener('jt-language-change', setupSeparatedUnitForms);
})();
