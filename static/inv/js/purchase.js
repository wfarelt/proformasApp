function updateSubtotals() {
    let totalGeneral = 0;
    document.querySelectorAll('.purchase-row').forEach(row => {
        const quantityInput = row.querySelector('input[name$="-quantity"]');
        const priceInput = row.querySelector('input[name$="-unit_price"]');
        const subtotalCell = row.querySelector('.subtotal');

        if (quantityInput && priceInput && subtotalCell) {
            const qty = parseFloat(quantityInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            const subtotal = qty * price;
            subtotalCell.textContent = subtotal.toFixed(2);
            totalGeneral += subtotal;
        }
    });

    const totalDisplay = document.getElementById('total-general');
    if (totalDisplay) {
        totalDisplay.textContent = totalGeneral.toFixed(2);
    }
}

document.addEventListener('input', function(e) {
    if (e.target.name && (e.target.name.includes('quantity') || e.target.name.includes('unit_price'))) {
        updateSubtotals();
    }
});

document.addEventListener('DOMContentLoaded', updateSubtotals);