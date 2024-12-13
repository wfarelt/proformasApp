from django.db import models
from django.utils import timezone

# Create your models here.

# CLIENTE
class Cliente(models.Model):
    name = models.CharField(max_length=100)
    nit = models.CharField(blank=True, null=True, max_length=15)
    email = models.EmailField(blank=True, null=True, max_length=100)
    phone = models.CharField(blank=True, null=True, max_length=15)
    address = models.CharField(blank=True, null=True, max_length=100)
    
    def __str__(self):
        return self.name

# MARCA
class Brand(models.Model):
    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        ordering = ['name']

    def __str__(self):
        return self.name

# PRODUCTO
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0, blank=True, null=True)
    location = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['id']

    # devolver precio de producto
    def get_precio(self):
        return self.precio

# PROFORMA
class Proforma(models.Model):
    # ESTADO (PENDIENTE, EJECUTADO, ANULADO)
    ESTADO = (
        ('PENDIENTE', 'Pendiente'),
        ('EJECUTADO', 'Ejecutado'),
        ('ANULADO', 'Anulado'),
    )
    fecha = models.DateTimeField(default=timezone.now)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, blank=True, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estado = models.CharField(max_length=10, choices=ESTADO, default='PENDIENTE')

    def __str__(self):
        return str(self.id)
    
    class Meta:
        verbose_name = "Proforma"
        verbose_name_plural = "Proformas" 

# DETALLE PROFORMA
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
        ordering = ['id']

    def __str__(self):
        return self.name

