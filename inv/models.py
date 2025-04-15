from django.db import models
from core.models import Producto, User, Supplier
# Create your models here.

# INGRESOS
class ProductEntry(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Anulado'),
    ]

    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Ingreso {self.id} - {self.date.strftime('%Y-%m-%d')} ({self.get_status_display()})"

class ProductEntryDetail(models.Model):
    entry = models.ForeignKey(ProductEntry, on_delete=models.CASCADE, related_name='details')  # Relación con el ingreso
    product = models.ForeignKey(Producto, on_delete=models.CASCADE)  # Producto ingresado
    quantity = models.PositiveIntegerField()  # Cantidad ingresada
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Costo unitario del producto

    def subtotal(self):
        return self.quantity * self.unit_cost
    
    # Costro del producto
    def cost(self):
        return self.product.cost
    
    def __str__(self):
        return f"{self.product.nombre} - {self.quantity} unidades"

# COMPRAS

class Purchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Anulado'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"
    
class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Producto, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.product.nombre} - {self.quantity} unidades"