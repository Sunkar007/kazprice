// Client-side handlers for favorites and cart
document.addEventListener('DOMContentLoaded', function(){
  // toggle favorite (works with /toggle_favorite/<id>) — update only the clicked heart element
  document.body.addEventListener('click', function(e){
    const btn = e.target.closest('[data-fav-btn]');
    if(!btn) return;
    e.preventDefault();

    const pid = btn.dataset.productId;
    if(!pid) return;

    // Temporarily disable to avoid duplicate clicks
    btn.disabled = true;

    fetch(`/toggle_favorite/${encodeURIComponent(pid)}`, { method: 'POST', headers: {'Content-Type':'application/json'} })
      .then(r => r.json())
      .then(data => {
        if(!data || !data.status) return;
        const isAdded = (data.status === 'added');
        const icon = btn.querySelector('.fav-icon');

        if(icon){
          if(isAdded) icon.classList.add('fav-on'); else icon.classList.remove('fav-on');
          // quick feedback pulse
          icon.classList.add('pulse');
          setTimeout(()=> icon.classList.remove('pulse'), 180);
        }

        btn.setAttribute('aria-pressed', isAdded ? 'true' : 'false');
        btn.setAttribute('data-favorite-state', isAdded ? 'true' : 'false');
      })
      .catch(err => console.error('toggle_favorite failed', err))
      .finally(()=> btn.disabled = false);
  });

  // add to cart
  document.body.addEventListener('click', function(e){
    const t = e.target.closest('[data-addcart-btn]');
    if(!t) return;
    e.preventDefault();
    const pid = t.dataset.productId;
    const qty = t.dataset.qty || 1;
    fetch('/add_to_cart', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({product_id: pid, quantity: qty})
    }).then(r => r.json()).then(data => {
      if(data && data.cart_count !== undefined){
      // update cart badge if exists (both data attribute and id)
      const badge = document.querySelector('[data-cart-count]');
      if(badge) badge.textContent = data.cart_count;
      const badgeById = document.getElementById('cart-count');
      if(badgeById) badgeById.textContent = data.cart_count;
        // simple feedback
        t.classList.add('added');
        setTimeout(()=> t.classList.remove('added'), 900);
      }
    }).catch(console.error);
  });

  // remove from favorites (on /favorites page) — AJAX delete and remove DOM element
  document.body.addEventListener('click', function(e){
    const rem = e.target.closest('[data-remove-fav]');
    if(!rem) return;
    e.preventDefault();

    const pid = rem.dataset.productId;
    if(!pid) return;

    rem.disabled = true;

    fetch(`/remove_favorite/${encodeURIComponent(pid)}`, { method: 'POST', headers: {'Content-Type':'application/json'} })
      .then(r => r.json().catch(()=>null))
      .then(data => {
        if(!data) return;
        if(data.status === 'removed'){
          // remove the closest product-card
          let card = rem.closest('.product-card');
          if(!card){
            // fallback: find by data attribute
            card = document.querySelector(`.product-card[data-product-id="${pid}"]`);
          }
          if(card && card.parentNode){
            card.parentNode.removeChild(card);
          }

          // If an equivalent heart exists elsewhere on the page, update it
          document.querySelectorAll(`[data-fav-btn][data-product-id="${pid}"]`).forEach(b=>{
            const icon = b.querySelector('.fav-icon');
            if(icon) icon.classList.remove('fav-on');
            b.setAttribute('aria-pressed','false');
            b.setAttribute('data-favorite-state','false');
          });

          // If favorites grid is now empty, show placeholder message
          const grid = document.getElementById('favoritesGrid');
          if(grid){
            const has = grid.querySelector('.product-card');
            if(!has){
              grid.innerHTML = '<div class="form-card mt-3">Сізде таңдалған тауарлар жоқ.</div>';
            }
          }
        }
      })
      .catch(err => console.error('remove_favorite failed', err))
      .finally(()=> rem.disabled = false);
  });

  /* ---------- cart quantity updates (AJAX) ---------- */
  const fmtMoney = (v) => new Intl.NumberFormat('ru-RU').format(v) + ' ₸';

  function sendUpdateQuantity(pid, qty){
    // send update and reflect new item price and cart total
    return fetch('/update_cart_quantity', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({product_id: pid, quantity: qty})
    }).then(r => r.json());
  }

  // delegate quantity + / - buttons and remove button
  document.body.addEventListener('click', function(e){
    // remove item button
    const remCart = e.target.closest('[data-remove-cart]');
    if(remCart){
      e.preventDefault();
      const pid = remCart.dataset.productId;
      if(!pid) return;
      remCart.disabled = true;
      fetch(`/remove_from_cart/${encodeURIComponent(pid)}`, { method: 'POST', headers: {'Content-Type':'application/json'} })
        .then(r => r.json().catch(()=>null))
        .then(data => {
          if(!data) return;
          // if removed, update DOM
          if(data.status === 'removed'){
            const row = document.querySelector(`tr[data-product-id="${pid}"]`);
            if(row) row.remove();

            // update total
            const cartTotalEl = document.getElementById('cartTotal');
            if(cartTotalEl) cartTotalEl.textContent = fmtMoney(data.updated_total).replace(' ₸','');

            // update navbar badge
            if(data.cart_count !== undefined){
              const badge = document.querySelector('[data-cart-count]'); if(badge) badge.textContent = data.cart_count;
              const badgeById = document.getElementById('cart-count'); if(badgeById) badgeById.textContent = data.cart_count;
            }

            // if cart is now empty, show placeholder
            const grid = document.getElementById('cartItems');
            if(grid && !grid.querySelector('tr')){
              grid.innerHTML = '<tr><td colspan="6"><div class="form-card mt-3">Себет бос.</div></td></tr>';
            }
          }
        }).catch(console.error).finally(()=> remCart.disabled = false);
      return;
    }
    const de = e.target.closest('[data-qty-decr]');
    if(de){
      e.preventDefault();
      const pid = de.dataset.productId;
      const input = document.querySelector(`[data-qty-input][data-product-id="${pid}"]`);
      if(!input) return;
      let qty = parseInt(input.value || '0', 10) || 0;
      qty = Math.max(0, qty - 1);
      input.value = qty;
      // if qty becomes 0, server will remove item
      sendUpdateQuantity(pid, qty).then(data => {
        if(!data) return;
        if(data.updated_price === 0){
          // remove the row
          const row = document.querySelector(`tr[data-product-id="${pid}"]`) || input.closest('tr');
          if(row) row.remove();
          // if cart empty, render placeholder
          const grid = document.getElementById('cartItems');
          if(grid && !grid.querySelector('tr')){
            grid.innerHTML = '<tr><td colspan="6"><div class="form-card mt-3">Себет бос.</div></td></tr>';
            const cartTotalEl = document.getElementById('cartTotal'); if(cartTotalEl) cartTotalEl.textContent = '0';
          }
        } else {
          const totalEl = document.querySelector(`[data-item-total-id="${pid}"]`);
          if(totalEl) totalEl.textContent = fmtMoney(data.updated_price).replace(' ₸','');
        }
        const cartTotalEl = document.getElementById('cartTotal');
        if(cartTotalEl) cartTotalEl.textContent = fmtMoney(data.updated_total).replace(' ₸','');
        if(data.cart_count !== undefined){
          const badge = document.querySelector('[data-cart-count]'); if(badge) badge.textContent = data.cart_count;
          const badgeById = document.getElementById('cart-count'); if(badgeById) badgeById.textContent = data.cart_count;
        }
      }).catch(console.error);
      return;
    }

    const inc = e.target.closest('[data-qty-incr]');
    if(inc){
      e.preventDefault();
      const pid = inc.dataset.productId;
      const input = document.querySelector(`[data-qty-input][data-product-id="${pid}"]`);
      if(!input) return;
      let qty = parseInt(input.value || '0', 10) || 0;
      qty = qty + 1;
      input.value = qty;
      sendUpdateQuantity(pid, qty).then(data => {
        if(!data) return;
        const totalEl = document.querySelector(`[data-item-total-id="${pid}"]`);
        if(totalEl) totalEl.textContent = fmtMoney(data.updated_price).replace(' ₸','');
        const cartTotalEl = document.getElementById('cartTotal');
        if(cartTotalEl) cartTotalEl.textContent = fmtMoney(data.updated_total).replace(' ₸','');
        if(data.cart_count !== undefined){
          const badge = document.querySelector('[data-cart-count]'); if(badge) badge.textContent = data.cart_count;
          const badgeById = document.getElementById('cart-count'); if(badgeById) badgeById.textContent = data.cart_count;
        }
      }).catch(console.error);
      return;
    }
  });

  // input change handler (debounce)
  let qtyTimer = null;
  document.body.addEventListener('input', function(e){
    const input = e.target.closest('[data-qty-input]');
    if(!input) return;
    const pid = input.dataset.productId;
    let qty = parseInt(input.value || '0', 10) || 0;
    qty = Math.max(0, qty);
    input.value = qty;

    // debounce rapid typing
    if(qtyTimer) clearTimeout(qtyTimer);
    qtyTimer = setTimeout(()=>{
      sendUpdateQuantity(pid, qty).then(data=>{
        if(!data) return;
        if(data.updated_price === 0){
          // removed
          const row = document.querySelector(`tr[data-product-id="${pid}"]`) || input.closest('tr');
          if(row) row.remove();
          // if cart became empty, show placeholder
          const grid = document.getElementById('cartItems');
          if(grid && !grid.querySelector('tr')){
            grid.innerHTML = '<tr><td colspan="6"><div class="form-card mt-3">Себет бос.</div></td></tr>';
            const cartTotalEl = document.getElementById('cartTotal'); if(cartTotalEl) cartTotalEl.textContent = '0';
          }
        } else {
          const totalEl = document.querySelector(`[data-item-total-id="${pid}"]`);
          if(totalEl) totalEl.textContent = fmtMoney(data.updated_price).replace(' ₸','');
        }
        const cartTotalEl = document.getElementById('cartTotal');
        if(cartTotalEl) cartTotalEl.textContent = fmtMoney(data.updated_total).replace(' ₸','');
        if(data.cart_count !== undefined){
          const badge = document.querySelector('[data-cart-count]'); if(badge) badge.textContent = data.cart_count;
          const badgeById = document.getElementById('cart-count'); if(badgeById) badgeById.textContent = data.cart_count;
        }
      }).catch(console.error);
    }, 300);
  });

  // clear cart
  const clearBtn = document.getElementById('clearCartBtn');
  if(clearBtn){
    clearBtn.addEventListener('click', function(e){
      e.preventDefault();
      clearBtn.disabled = true;
      fetch('/clear_cart', { method: 'POST', headers: {'Content-Type':'application/json'} })
        .then(r=>r.json())
        .then(data => {
          if(data && data.status === 'cleared'){
            // remove all rows
            const grid = document.getElementById('cartItems');
            if(grid){
              grid.innerHTML = '<tr><td colspan="6"><div class="form-card mt-3">Себет бос.</div></td></tr>';
            }
            const cartTotalEl = document.getElementById('cartTotal');
            if(cartTotalEl) cartTotalEl.textContent = '0';
            // update cart-count in navbar
            const badge = document.querySelector('[data-cart-count]'); if(badge) badge.textContent = 0;
            const badgeById = document.getElementById('cart-count'); if(badgeById) badgeById.textContent = 0;
          }
        }).catch(console.error).finally(()=> clearBtn.disabled = false);
    });
  }
});
