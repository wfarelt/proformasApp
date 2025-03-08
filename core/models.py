from django.db import models
from django.utils import timezone

from urllib.parse import quote
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        if not email:
            raise ValueError('The Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        user.set_password(password)  # Encripta la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password):
        user = self.create_user(email, name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Necesario para Django Admin
    is_superuser = models.BooleanField(default=False)  # Necesario para permisos

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Se usará para el login
    REQUIRED_FIELDS = ['name']  # Campos obligatorios además de email

    def __str__(self):
        return self.email


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
    cost = models.DecimalField(default=0, max_digits=10, decimal_places=2, blank=True, null=True)
    precio = models.DecimalField(default=0, max_digits=10, decimal_places=2)
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
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="proformas", default=1)

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

