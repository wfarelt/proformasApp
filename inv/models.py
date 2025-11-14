from django.db import models
from core.models import Producto, User, Supplier
# Para modificar el modelo de movimiento de inventario
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

# COMPRAS

class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Anulado'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"
    
    class Meta:
        verbose_name = 'Purchase'
        verbose_name_plural = 'Purchases'
        # Ordenar por id
        ordering = ['-id']
        
    @property
    def movement(self):
        from .models import Movement  # Importación local para evitar ciclos
        ct = ContentType.objects.get_for_model(Purchase)
        return Movement.objects.filter(
            content_type=ct,
            object_id=self.id,
            movement_type='IN'
        ).first()
           
class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Producto, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def subtotal(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.product.nombre} - {self.quantity} unidades"


# MOVIMIENTOS DE INVENTARIO

class Movement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Ingreso'),
        ('OUT', 'Egreso'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
    ]

    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')

    # Generic relation for purchase or proforma
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_document = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.movement_type} #{self.id} - {self.status}"
    
    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())  # ✅ usamos la propiedad

class MovementItem(models.Model):
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Producto, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_after_movement = models.IntegerField(null=True, blank=True)
    observation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.nombre} ({self.quantity})"

    @property
    def subtotal(self):
        price = self.unit_price or self.product.cost or 0
        return price * self.quantity

    
    