
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => links.classList.toggle('open'));
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.card, .service-card, .admin-panel, .login-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(18px)';
    el.style.transition = 'opacity .55s ease, transform .55s ease';
    observer.observe(el);
  });

  window.addEventListener('scroll', () => {
    const nav = document.querySelector('.main-nav');
    if (!nav) return;
    nav.style.boxShadow = window.scrollY > 50 ? '0 2px 20px rgba(58,34,24,0.08)' : 'none';
  });

  const qtyInputs = document.querySelectorAll('.qty-input');
  const totalLabel = document.getElementById('cart-total');
  const formatSoles = (value) => `S/ ${value.toFixed(2)}`;
  function recalcCart() {
    let total = 0;
    qtyInputs.forEach(input => {
      const row = input.closest('tr');
      const price = parseFloat(input.dataset.price || '0');
      const qty = Math.max(1, parseInt(input.value || '1', 10));
      const subtotal = price * qty;
      total += subtotal;
      const cell = row.querySelector('.line-subtotal');
      if (cell) cell.textContent = formatSoles(subtotal);
    });
    if (totalLabel) totalLabel.textContent = formatSoles(total);
  }
  qtyInputs.forEach(input => input.addEventListener('input', recalcCart));
});
