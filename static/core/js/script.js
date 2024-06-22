// scripts.js

document.addEventListener('DOMContentLoaded', function() {
    // Selecciona todos los inputs que pueden afectar el subtotal
    const inputs = document.querySelectorAll('input[type="number"]');

    // Función para actualizar el subtotal correspondiente
    function actualizarSubtotal(event) {
        const input = event.target;
        const id = input.id;
        const index = id.match(/\d+/)[0];  // Extrae el número del id

        const cantidadInput = document.getElementById(`cantidad${index}`);
        const precioInput = document.getElementById(`precio${index}`);
        const subtotalInput = document.getElementById(`subtotal${index}`);

        const cantidad = parseFloat(cantidadInput.value) || 0;
        const precio = parseFloat(precioInput.value) || 0;
        const subtotal = cantidad * precio;
        subtotalInput.value = subtotal.toFixed(2);
    }

    // Añadir event listeners a todos los inputs de cantidad y precio
    inputs.forEach(input => {
        if (input.id.startsWith('cantidad') || input.id.startsWith('precio')) {
            input.addEventListener('input', actualizarSubtotal);
        }
    });

    // Inicializar todos los subtotales al cargar la página
    inputs.forEach(input => {
        if (input.id.startsWith('cantidad') || input.id.startsWith('precio')) {
            actualizarSubtotal({ target: input });
        }
    });
});
