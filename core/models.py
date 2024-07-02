from django.db import models
from django.utils import timezone

# Create your models here.

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0, blank=True, null=True)
    location = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    # devolver precio de producto
    def get_precio(self):
        return self.precio


class Proforma(models.Model):
    fecha = models.DateTimeField(default=timezone.now)
    cliente = models.CharField(max_length=100, blank=True, null=True, default="Cliente")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return str(self.id)
    
    class Meta:
        verbose_name = "Proforma"
        verbose_name_plural = "Proformas" 


class Detalle(models.Model):
    proforma = models.ForeignKey(Proforma, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} en {self.proforma.id}"
    
    # LISTAR PRODUCTOS DE LA PROFORMA
    def productos_list(proforma):
        detalles = Detalle.objects.filter(proforma=proforma)
        return detalles

# CLIENTE
#name (string); #email (string); #phone (string); #address (string)
class Cliente(models.Model):
    name = models.CharField(max_length=100)
    nit = models.CharField(blank=True, null=True, max_length=15)
    email = models.EmailField(blank=True, null=True, max_length=100)
    phone = models.CharField(blank=True, null=True, max_length=15)
    address = models.CharField(blank=True, null=True, max_length=100)
    
    def __str__(self):
        return self.name


# PROVEEDOR
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, max_length=100)
    address = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ['name']

    def __str__(self):
        return self.name