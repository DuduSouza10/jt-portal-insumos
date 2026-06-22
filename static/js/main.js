const productGrid = document.getElementById('productGrid');
const productSearch = document.getElementById('productSearch');
const refreshProducts = document.getElementById('refreshProducts');
const emptyState = document.getElementById('emptyState');
const cartItems = document.getElementById('cartItems');
const cartCount = document.getElementById('cartCount');
const clearCart = document.getElementById('clearCart');
const submitRequest = document.getElementById('submitRequest');
const cartMessage = document.getElementById('cartMessage');
const requestNote = document.getElementById('requestNote');
const downloadLastPdf = document.getElementById('downloadLastPdf');

let products = [];
let cart = new Map();
let debounceTimer = null;

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

async function loadProducts() {
  const q = productSearch.value.trim();
  productGrid.innerHTML = `<div class="card empty-state">${jtText('Carregando insumos...')}</div>`;
  emptyState.classList.add('hidden');
  const response = await fetch(`/api/products?q=${encodeURIComponent(q)}`);
  products = await response.json();
  renderProducts();
}

function renderProducts() {
  productGrid.innerHTML = '';
  if (!products.length) {
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');
  products.forEach((product, index) => {
    const card = document.createElement('article');
    card.className = 'product-card card';
    card.style.animationDelay = `${Math.min(index * 0.045, 0.45)}s`;

    const unit = product.unit_measure || 'un';
    const priceBadge = product.show_price ? `<span class="badge red">${escapeHtml(product.price)} / ${escapeHtml(unit)}</span>` : '';
    const unitBadge = `<span class="badge">${jtText('Unidade')}: ${escapeHtml(unit)}</span>`;
    const stockBadge = product.show_stock ? `<span class="badge">${jtText('Estoque')}: ${product.stock_quantity} ${escapeHtml(unit)}</span>` : '';
    const limitBadge = product.limit !== null && product.limit !== undefined ? `<span class="badge">${jtText('Limite')}: ${product.limit} ${escapeHtml(unit)}</span>` : `<span class="badge">${jtText('Sem limite definido')}</span>`;

    card.innerHTML = `
      <div class="product-head">
        <span class="product-icon">📦</span>
        <span class="product-category">${escapeHtml(product.category)}</span>
      </div>
      <div>
        <h3>${escapeHtml(product.name)}</h3>
        <p>${escapeHtml(product.description || jtText('Sem descrição cadastrada.'))}</p>
      </div>
      <div class="meta-row">
        ${priceBadge}
        ${unitBadge}
        ${stockBadge}
        ${limitBadge}
      </div>
      <div class="add-row">
        <input type="number" min="1" value="1" aria-label="${jtText('Quantidade')}">
        <button class="btn primary" type="button">${jtText('Adicionar')}</button>
      </div>
    `;
    const qtyInput = card.querySelector('input');
    const button = card.querySelector('button');
    button.addEventListener('click', () => {
      const quantity = parseInt(qtyInput.value, 10);
      if (!quantity || quantity <= 0) {
        setMessage(jtText('Informe uma quantidade válida.'), 'err');
        return;
      }
      const current = cart.get(product.id)?.quantity || 0;
      if (product.limit !== null && product.limit !== undefined && current + quantity > product.limit) {
        setMessage(jtText(`Limite de insumos excedido para ${product.name}. Limite permitido: ${product.limit}.`), 'err');
        return;
      }
      cart.set(product.id, { product, quantity: current + quantity });
      renderCart();
      setMessage(jtText(`${product.name} adicionado à solicitação.`), 'ok');
    });
    productGrid.appendChild(card);
  });
}

function renderCart() {
  cartItems.innerHTML = '';
  const values = Array.from(cart.values());
  const totalQty = values.reduce((sum, item) => sum + item.quantity, 0);
  cartCount.textContent = `${totalQty} ${totalQty === 1 ? jtText('item') : jtText('itens')}`;

  if (!values.length) {
    cartItems.innerHTML = `<div class="muted center">${jtText('Sua lista está vazia.')}</div>`;
    return;
  }

  values.forEach((item, index) => {
    const div = document.createElement('div');
    div.className = 'cart-item';
    div.style.animationDelay = `${Math.min(index * 0.035, 0.25)}s`;
    div.innerHTML = `
      <div>
        <strong>${escapeHtml(item.product.name)}</strong>
        <span>${item.product.show_price ? escapeHtml(item.product.price) : jtText('Valor oculto')} / ${escapeHtml(item.product.unit_measure || 'un')}</span>
      </div>
      <input type="number" min="1" value="${item.quantity}">
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
      if (item.product.limit !== null && item.product.limit !== undefined && quantity > item.product.limit) {
        input.value = item.quantity;
        setMessage(jtText(`Limite de insumos excedido para ${item.product.name}. Limite permitido: ${item.product.limit}.`), 'err');
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
  submitRequest.disabled = true;
  setMessage(jtText('Enviando solicitação...'), '');
  try {
    const response = await fetch('/api/requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: values.map(item => ({ product_id: item.product.id, quantity: item.quantity })),
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
