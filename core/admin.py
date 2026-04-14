from django.contrib import admin
from .models import Producto, Proforma, Cliente, Detalle, Brand, \
    Supplier, User, Company
from import_export.admin import ImportExportModelAdmin
from .resources import ProductResource

from django.contrib.auth.admin import UserAdmin
from .forms import UserCreationForm, UserChangeForm

class UserAdmin(UserAdmin):
    finaly = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Información personal', {'fields': ('name', 'company', 'role')}),
        ('Estado', {'fields': ('is_active',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'name',
                'company',
                'role',
                'password1',
                'password2',
                'is_active',
            )}
         ),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('id', 'username', 'email', 'name', 'company', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'company')
    fieldsets = finaly
    search_fields = ('username', 'email', 'name', 'company__name')
    ordering = ('id',)

admin.site.site_header = 'Sistema de Inventario'
admin.site.site_title = 'Sistema de Inventario'
admin.site.index_title = 'Administración'

admin.site.register(User, UserAdmin)

class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'tax_id', 'email', 'city', 'currency', 'enable_product_kits', 'enable_product_recommendations', 'is_active')
    list_filter = ('is_active', 'enable_product_kits', 'enable_product_recommendations', 'currency')
    search_fields = ('name', 'tax_id', 'email')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'logo', 'tax_id', 'email', 'phone')
        }),
        ('Ubicación', {
            'fields': ('address', 'city')
        }),
        ('Configuración', {
            'fields': ('currency', 'enable_product_kits', 'enable_product_recommendations', 'website', 'industry', 'established_date')
        }),
        ('Campos Personalizados para Productos', {
            'fields': ('product_custom_fields_config',),
            'description': 'Define campos adicionales para productos. Formato JSON. Ejemplo: {"color": {"type": "text", "label": "Color", "required": false}, "garantia": {"type": "number", "label": "Garantía (meses)", "required": true}}'
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )

admin.site.register(Company, CompanyAdmin)

class ProformaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'cliente', 'usuario_username', 'estado', 'total', 'company')
    list_filter = ('estado', 'company', 'fecha')
    search_fields = ('id', 'cliente__name', 'usuario__username', 'usuario__name')
    ordering = ('-fecha',)

    @admin.display(description='Username')
    def usuario_username(self, obj):
        return obj.usuario.username if obj.usuario else '-'

admin.site.register(Proforma, ProformaAdmin)

admin.site.register(Detalle)

admin.site.register(Cliente)

admin.site.register(Brand)

admin.site.register(Supplier)

class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    
    list_display = ('nombre', 'descripcion', 'cost', 'precio', 'stock')
    search_fields = ('nombre', 'descripcion')

admin.site.register(Producto, ProductAdmin)
