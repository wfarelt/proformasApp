from django.contrib import admin
from .models import Producto, Proforma, Cliente, Detalle, Brand, \
    Supplier, User, Company
from import_export.admin import ImportExportModelAdmin
from .resources import ProductResource

from django.contrib.auth.admin import UserAdmin
from .forms import UserCreationForm, UserChangeForm

class UserAdmin(UserAdmin):
    finaly = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('name', 'company')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'company', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')}
         ),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('id','email', 'name', 'company', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    fieldsets = finaly
    search_fields = ('email', 'name', 'company')
    ordering = ('id',)

admin.site.site_header = 'Sistema de Inventario'
admin.site.site_title = 'Sistema de Inventario'
admin.site.index_title = 'Administración'

admin.site.register(User, UserAdmin)

admin.site.register(Company)

admin.site.register(Proforma)

admin.site.register(Detalle)

admin.site.register(Cliente)

admin.site.register(Brand)

admin.site.register(Supplier)

class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    
    list_display = ('nombre', 'descripcion', 'cost', 'precio', 'stock')
    search_fields = ('nombre', 'descripcion')

admin.site.register(Producto, ProductAdmin)
