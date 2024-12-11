from decimal import Decimal
from django.utils import timezone
from django.db import models
from core.models import Producto, Supplier
# Create your models here.

# MOVIMIENTO
class Movement(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Ingreso'),
        ('OUT', 'Egreso'),
    ]
    movement_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    date = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)  # Solo para ingresos
    total_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Movement"
        verbose_name_plural = "Movements"

# DETALLE DE MOVIMIENTO
class MovementDetail(models.Model):
    movement = models.ForeignKey(Movement, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Producto, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Para ingresos
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quantity} x {self.product.nombre} ({self.movement.get_movement_type_display()})"

    def save(self, *args, **kwargs):
        # Calcula el subtotal
        self.subtotal = self.quantity * self.cost

        # Actualizar total_quantity en el movimiento
        self.movement.total_quantity += self.quantity
        self.movement.save()

        # Actualizar precio del producto * 1.35 
        if self.movement.movement_type == 'IN':
            self.product.precio = self.cost * Decimal('1.35')
            self.product.save()
        
        # Actualizar stock
        if self.movement.movement_type == 'IN':
            self.product.stock += self.quantity
        elif self.movement.movement_type == 'OUT':
            if self.product.stock < self.quantity:
                raise ValueError("Stock insuficiente para realizar el egreso.")
            self.product.stock -= self.quantity

        # Guarda los cambios en el producto
        self.product.save()

        # Llama al método `save` del modelo base
        super().save(*args, **kwargs)

    