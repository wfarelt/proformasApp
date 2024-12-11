from django.test import TestCase
from core.models import Producto
from inv.models import Movement, MovementDetail
from django.utils import timezone


class MovementTests(TestCase):

    def setUp(self):
        # Crear un producto con stock inicial
        self.producto = Producto.objects.create(
            nombre="Laptop",
            descripcion="Laptop de alta gama",
            precio=1500.00,
            stock=10
        )

    def test_egreso_resta_stock(self):
        """Validar que un egreso reduce el stock del producto."""
        # Crear un movimiento de egreso
        movimiento = Movement.objects.create(
            movement_type='OUT',
            date=timezone.now(),
            description="Venta de producto",
        )

        # MovimientosDetails
        md= MovementDetail.objects.create(
            movement=movimiento,
            product=self.producto,
            quantity=5,
        )

        md.save()

        # Refrescar el producto de la base de datos
        self.producto.refresh_from_db()

        # Validar que el stock se ha reducido correctamente
        self.assertEqual(self.producto.stock, 5)

    def test_egreso_sin_stock_insuficiente(self):
        """Validar que no se permite un egreso si no hay stock suficiente."""
        with self.assertRaises(ValueError):
            movimiento = Movement.objects.create(
                movement_type='OUT',
                date=timezone.now(),
                description="Intento de egreso sin stock",
            )
            # MovimientosDetails
            md= MovementDetail.objects.create(
                movement=movimiento,
                product=self.producto,
                quantity=15,
            )
            md.save()
            

        # Validar que el stock permanece igual
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
