document.addEventListener('DOMContentLoaded', function() {
    // Selecciona todos los inputs que pueden afectar el subtotal
    const inputs = document.querySelectorAll('input[type="number"]');

    // Función para actualizar el subtotal correspondiente
    function actualizarSubtotal(event) {
        const input = event.target;
        const id = input.id;
        const index = id.match(/\d+/)[0];  // Extrae el número del id

        const costInput = document.getElementById(`cost${index}`);
        const quantityInput = document.getElementById(`quantity${index}`);
        
        const subtotalInput = document.getElementById(`subtotal${index}`);

        const cost = parseFloat(costInput.value) || 0;
        const quantity = parseFloat(quantityInput.value) || 0;
        const subtotal = cost * quantity;
        
        subtotalInput.value = subtotal.toFixed(2);
    }

    // Añadir event listeners a todos los inputs de cantidad y precio
    inputs.forEach(input => {
        if (input.id.startsWith('quantity') || input.id.startsWith('cost')) {
            input.addEventListener('input', actualizarSubtotal);
        }
    });

    // Inicializar todos los subtotales al cargar la página
    inputs.forEach(input => {
        if (input.id.startsWith('quantity') || input.id.startsWith('cost')) {
            actualizarSubtotal({ target: input });
        }
    });

});
