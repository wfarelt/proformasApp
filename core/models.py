from django.db import models
from django.conf import settings
from django.utils import timezone

from urllib.parse import quote
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.

# EMPRESA
class Company(models.Model):
    CURRENCY_CHOICES = [
        ('BOB', 'Boliviano'),
        ('USD', 'Dólar estadounidense'),
        ('EUR', 'Euro'),
        # Agrega más monedas si lo necesitas
    ]
    name = models.CharField(max_length=255, unique=True)  # Nombre de la empresa
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)  # Logo de la empresa
    tax_id = models.CharField(max_length=50, unique=True)  # Identificación fiscal (RUC, NIT, etc.)
    phone = models.CharField(max_length=20, null=True, blank=True)  # Teléfono de contacto
    email = models.EmailField(unique=True)  # Correo electrónico
    address = models.TextField(null=True, blank=True)  # Dirección física
    city = models.CharField(max_length=100, null=True, blank=True)  # Ciudad
    website = models.URLField(null=True, blank=True)  # Sitio web
    established_date = models.DateField(null=True, blank=True)  # Fecha de fundación
    industry = models.CharField(max_length=100, null=True, blank=True)  # Industria o sector
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        verbose_name='Moneda'
    )  # Moneda predeterminada
    is_active = models.BooleanField(default=True)  # Estado activo/inactivo
    created_at = models.DateTimeField(auto_now_add=True)  # Fecha de creación
    updated_at = models.DateTimeField(auto_now=True)  # Última actualización

    def __str__(self):
        return self.name

# USUARIO
class UserManager(BaseUserManager):
    def create_user(self, username, email, name, password=None):
        if not username:
            raise ValueError('El nombre de usuario es obligatorio')
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        user = self.model(username=username, email=self.normalize_email(email), name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, name, password):
        user = self.create_user(username, email, name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, verbose_name="Usuario", default="user")
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, verbose_name="Nombre completo")
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name', 'company']

    def __str__(self):
        return self.email
    
    def is_in_group(self, group_name):
        """Verifica si el usuario pertenece a un grupo específico"""
        return self.groups.filter(name=group_name).exists()
    
    @property
    def is_admin(self):
        return self.is_in_group("Administrador")

# CLIENTE
class Cliente(models.Model):
    name = models.CharField(max_length=100)
    nit = models.CharField(blank=True, null=True, max_length=15)
    email = models.EmailField(blank=True, null=True, max_length=100)
    phone = models.CharField(blank=True, null=True, max_length=15)
    address = models.CharField(blank=True, null=True, max_length=100)
    status = models.BooleanField(default=True)
    
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
    latest_price = models.DecimalField(default=0, max_digits=10, decimal_places=2 )
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
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text="Descuento en porcentaje (ej. 10.00 para 10%)"
    )
    estado = models.CharField(max_length=10, choices=ESTADO, default='PENDIENTE')
    observacion = models.TextField(max_length=200, blank=True, null=True, help_text="Observaciones adicionales sobre la proforma")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="proformas", default=1)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proformas"
    )
    
    def save(self, *args, **kwargs):
        # Solo al crear (no actualizar), asignar la empresa actual del usuario
        if not self.pk and self.usuario and self.usuario.company:
            self.company = self.usuario.company
        super().save(*args, **kwargs)
    
    def total_neto(self):
        """Calcula el total después de aplicar el descuento porcentual."""
        descuento = (self.total * self.discount_percentage) / 100
        return max(self.total - descuento, 0)  # Asegura que no sea negativo
    
    def total_descuento(self):
        """Calcula el descuento total."""
        return self.total - self.total_neto()

    def __str__(self):
        return str(self.id)
    
    def proforma__cliente__name(self):
        return self.cliente.name if self.cliente else "Sin Cliente"
    
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

# KIT DE PRODUCTOS
class ProductKit(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Kit")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_kits")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="product_kits")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Kit de Productos"
        verbose_name_plural = "Kits de Productos"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_items_count(self):
        """Retorna la cantidad de productos en el kit"""
        return self.items.count()

class ProductKitItem(models.Model):
    kit = models.ForeignKey(ProductKit, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Ítem del Kit"
        verbose_name_plural = "Ítems del Kit"
        unique_together = ('kit', 'producto')
    
    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"
    
# HISTORIAL DE CAMBIOS DE PRECIO
class ProductPriceHistory(models.Model):

    CHANGE_TYPES = (
        ('INITIAL', 'Initial'),
        ('PURCHASE', 'Purchase'),
        ('MANUAL', 'Manual'),
        ('ADJUSTMENT', 'Adjustment'),
        ('DISCOUNT', 'Discount'),
        ('CORRECTION', 'Correction'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
        ('EXPIRED', 'Expirado'),
    )

    product = models.ForeignKey(
        'core.Producto',  # referencia string, evita circular import
        on_delete=models.PROTECT,
        related_name='price_history'
    )

    purchase = models.ForeignKey(
        'inv.Purchase',  # referencia string a Purchase en INV
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    new_price = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    cost_reference = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    margin_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    change_type = models.CharField(
        max_length=20, choices=CHANGE_TYPES
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='PENDING'
    )

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_price_changes'
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_price_changes'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Historial de Precio'
        verbose_name_plural = 'Historial de Precios'

    def __str__(self):
        return f"{self.product.nombre} - {self.new_price} ({self.status})"

