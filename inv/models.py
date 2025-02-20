from django.utils import timezone
from django.db import models, transaction
from core.models import Producto, Supplier
# Create your models here.

# MOVIMIENTO
class Movement(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Ingreso'),
        ('OUT', 'Egreso'),
    ]
    STATUS_CHOICES = [
        ('P', 'Pendiente'),
        ('F', 'Finalizado'),
        ('A', 'Anulado'),
    ]
    movement_type = models.CharField(max_length=3, choices=TYPE_CHOICES, default='IN')
    date = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)  # Solo para ingresos
    total_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    
    # Mostrar id, fecha(d/m/Y), tipo, total    
    def __str__(self):
        return f"{self.id} - {self.date.strftime('%d/%m/%Y')} - {self.get_movement_type_display()} - {self.total_quantity}"
    
    def update_total_quantity(self):
        """ Actualiza la cantidad total basada en los detalles. """
        self.total_quantity = self.details.aggregate(total=models.Sum('quantity'))['total'] or 0
        self.save()

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
        with transaction.atomic():  # Transacción para evitar inconsistencias
            if self.movement.movement_type == 'IN':
                self.product.stock += self.quantity
            elif self.movement.movement_type == 'OUT':
                if self.product.stock < self.quantity:
                    raise ValueError("Stock insuficiente para realizar el egreso.")
                self.product.stock -= self.quantity

            # Guarda el stock actualizado del producto
            self.product.save()

            # Guardar el detalle
            super().save(*args, **kwargs)


    @classmethod
    def productos_list(cls, movement):
        """ Obtiene todos los detalles de un movimiento """
        return cls.objects.filter(movement=movement)

    