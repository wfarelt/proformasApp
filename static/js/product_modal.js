(function () {
  var defaultImageUrl = '/static/img/no-image.png';

  function setText(id, value) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = value || '-';
  }

  function openModal() {
    var modalEl = document.getElementById('productImageModal');
    if (!modalEl) return;

    if (window.bootstrap && window.bootstrap.Modal) {
      // Compatibilidad Bootstrap 5
      if (typeof window.bootstrap.Modal.getOrCreateInstance === 'function') {
        var modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
        return;
      }

      // Compatibilidad Bootstrap 5 sin getOrCreateInstance
      var modalBs5 = new window.bootstrap.Modal(modalEl);
      modalBs5.show();
      return;
    }

    if (window.jQuery) {
      window.jQuery(modalEl).modal('show');
    }
  }

  window.showProductModal = async function (productId, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    if (!productId) return;

    try {
      var response = await fetch('/api/products/' + productId + '/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
      var data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'No se pudo cargar el producto');
      }

      var img = document.getElementById('product-modal-image');
      if (img) {
        img.src = data.imagen || defaultImageUrl;
        img.onerror = function () {
          img.src = defaultImageUrl;
        };
      }

      setText('product-modal-nombre', data.nombre);
      setText('product-modal-codigo', data.codigo);
      setText('product-modal-descripcion', data.descripcion);
      setText('product-modal-marca', data.marca);
      setText('product-modal-precio', data.precio);
      setText('product-modal-stock', data.stock);

      openModal();
    } catch (error) {
      console.error('Error abriendo modal de producto:', error);
      alert(error.message || 'No se pudo cargar la informacion del producto.');
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-product-modal-id]').forEach(function (el) {
      el.addEventListener('click', function (ev) {
        var productId = this.getAttribute('data-product-modal-id');
        window.showProductModal(productId, ev);
      });
    });
  });
})();
