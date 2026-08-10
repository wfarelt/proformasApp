from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.urls import reverse_lazy
from django.contrib import messages  # Importa el framework de mensajes
from django.core.paginator import Paginator
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db import IntegrityError, OperationalError
from django.db.models import CharField, Count, IntegerField, Max, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone
from django.utils.timezone import make_aware

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import json
import requests as http_requests
import weasyprint
from faker import Faker
from nlt import numlet as nl

from .models import Proforma, Producto, ProductStock, Detalle, Cliente, Supplier, Brand, Company, ProductKit, ProductKitItem, ProductPriceHistory, ExchangeRate, Warehouse
from .forms import ProductoForm, ClienteForm, SupplierForm, BrandForm, \
                    CustomPasswordChangeForm, UserProfileForm, ProductKitForm, ProductKitItemForm, ProductCatalogImportForm, CloudCatalogUploadForm, \
                    AdminUserCreateForm, AdminUserUpdateForm, CompanyDataForm, SuperadminCompanyForm, ExchangeRateForm
from .services.price_approval_service import PriceApprovalService
from core.services.auto_price_service import AutoPriceService
from core.services.product_catalog_import_service import ProductCatalogImportService

from inv.models import Movement, MovementItem  # Asegúrate de importar tus modelos correctamente

from .services.price_evaluation_service import PriceEvaluationService
from .services.inventory_service import apply_warehouse_stock_change
from .services.warehouse_access_service import WarehouseAccessDenied, accessible_warehouses, default_user_warehouse, resolve_user_warehouse
from .custom_attributes import ProductCustomAttributes

# Create your views here.

PROFORMA_BASE_CURRENCY = 'USD'
PROFORMA_REFERENCE_CURRENCY = 'BOB'
DEFAULT_USD_BOB_RATE = Decimal('6.960000')

# HOME
@login_required(login_url='login')
def home(request):
    if getattr(request.user, 'is_superadmin', False):
        context = {
            'quanty_companies': Company.objects.count(),
            'quanty_users': get_user_model().objects.count(),
            'active_companies': Company.objects.filter(is_active=True).count(),
            'custom_configured_companies': Company.objects.exclude(product_custom_fields_config={}).count(),
        }
        return render(request, 'core/config_dashboard.html', context)

    quanty_products = Producto.objects.count()
    quanty_clients = Cliente.objects.count()
    quanty_suppliers = Supplier.objects.count()
    quanty_proformas = Proforma.objects.count()
    context = {
        'quanty_products': quanty_products,
        'quanty_clients':quanty_clients,
        'quanty_suppliers':quanty_suppliers,
        'quanty_proformas':quanty_proformas
    }
    return render(request, 'core/home.html', context)

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'core/registration/change_password.html'
    success_url = reverse_lazy('edit_profile')

    def form_valid(self, form):
        messages.success(self.request, "Tu contraseña ha sido cambiada correctamente.")
        return super().form_valid(form)

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user, current_user=request.user)
        if form.is_valid():
            form.save()
            return redirect('home')  # Cambia por tu vista de perfil si la tienes
    else:
        form = UserProfileForm(instance=user, current_user=request.user)
    
    return render(request, 'core/registration/edit_profile.html', {'form': form})


@login_required(login_url='login')
def company_edit(request):
    if not is_admin(request.user):
        messages.error(request, 'No tienes permisos para editar los datos de la empresa.')
        return redirect('home')

    company = request.user.company
    if not company:
        messages.warning(request, 'Tu usuario no tiene una empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        form = CompanyDataForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos de la empresa actualizados correctamente.')
            return redirect('company_edit')
    else:
        form = CompanyDataForm(instance=company)

    return render(request, 'core/company/company_form.html', {
        'form': form,
        'title': 'Datos de la empresa',
        'company': company,
    })


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_superadmin', False))
def superadmin_company_list(request):
    companies = Company.objects.all().order_by('name')
    return render(request, 'core/company/company_superadmin_list.html', {
        'title': 'Configuración de empresas',
        'companies': companies,
    })


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_superadmin', False))
def superadmin_company_edit(request, company_id):
    company = get_object_or_404(Company, pk=company_id)

    if request.method == 'POST':
        form = SuperadminCompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración de empresa actualizada correctamente.')
            return redirect('superadmin_company_edit', company_id=company.id)
    else:
        form = SuperadminCompanyForm(instance=company)

    return render(request, 'core/company/company_form.html', {
        'form': form,
        'title': f'Configurar empresa: {company.name}',
        'company': company,
        'back_url_name': 'superadmin_company_list',
    })


@login_required(login_url='login')
@login_required(login_url='login')
def get_bcb_exchange_rate(request):
    """Proxy hacia la API del BCB para obtener el tipo de cambio oficial actual."""
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Sin permisos'}, status=403)
    try:
        resp = http_requests.get(
            'https://apibcb.cucu.bo/api/v1/tc/oficial',
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        tc = data.get('tc_oficial', {})
        valor = tc.get('valor')
        if valor is None:
            return JsonResponse({'success': False, 'error': 'La API no devolvió el campo valor'}, status=502)
        return JsonResponse({
            'success': True,
            'valor': valor,
            'moneda': tc.get('moneda', 'USD/BOB'),
            'fecha': tc.get('fecha', ''),
        })
    except http_requests.exceptions.Timeout:
        return JsonResponse({'success': False, 'error': 'La API del BCB no respondió a tiempo'}, status=504)
    except Exception:
        return JsonResponse({'success': False, 'error': 'No se pudo obtener el tipo de cambio del BCB'}, status=502)


def exchange_rate_list_create(request):
    if not is_admin(request.user):
        messages.error(request, 'No tienes permisos para administrar tipos de cambio.')
        return redirect('home')

    company = request.user.company
    if not company:
        messages.warning(request, 'Tu usuario no tiene una empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        form = ExchangeRateForm(request.POST, instance=ExchangeRate(company=company))
        if form.is_valid():
            exchange_rate = form.save(commit=False)
            exchange_rate.company = company
            exchange_rate.created_by = request.user
            try:
                with transaction.atomic():
                    # Si la nueva tasa queda activa, desactivar el resto del mismo par.
                    if exchange_rate.is_active:
                        ExchangeRate.objects.filter(
                            company=company,
                            from_currency=exchange_rate.from_currency,
                            to_currency=exchange_rate.to_currency,
                            is_active=True,
                        ).update(is_active=False)

                    exchange_rate.save()
                messages.success(request, 'Tipo de cambio guardado correctamente.')
                return redirect('exchange_rate_list')
            except IntegrityError:
                existing_rate = ExchangeRate.objects.filter(
                    company=company,
                    from_currency=exchange_rate.from_currency,
                    to_currency=exchange_rate.to_currency,
                    valid_from=exchange_rate.valid_from,
                ).first()

                # Idempotencia: si ya existe exactamente el mismo registro, tratarlo como éxito.
                if (
                    existing_rate
                    and existing_rate.rate == exchange_rate.rate
                    and existing_rate.is_active == exchange_rate.is_active
                ):
                    messages.success(request, 'Tipo de cambio ya registrado anteriormente (doble envío detectado).')
                else:
                    messages.warning(
                        request,
                        'Ya existe un tipo de cambio para esa combinación de monedas y fecha. '
                        'Si necesitas otro valor, edita el registro existente o usa otra fecha.'
                    )
                return redirect('exchange_rate_list')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ExchangeRateForm(
            instance=ExchangeRate(company=company),
            initial={'from_currency': PROFORMA_BASE_CURRENCY, 'to_currency': PROFORMA_REFERENCE_CURRENCY}
        )

    rates = ExchangeRate.objects.filter(company=company).order_by('-valid_from', '-created_at')
    return render(request, 'core/company/exchange_rate_form.html', {
        'title': 'Tipos de cambio',
        'form': form,
        'rates': rates,
        'company': company,
    })


class UserListView(LoginRequiredMixin, ListView):
    model = get_user_model()
    template_name = 'core/user/user_list.html'
    context_object_name = 'usuarios'
    paginate_by = 10
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, 'No tienes permisos para administrar usuarios.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.GET.get('q')
        qs = get_user_model().objects.exclude(role='SUPERADMIN').order_by('name', 'username')

        if self.request.user.company_id:
            qs = qs.filter(company=self.request.user.company)

        if query:
            qs = qs.filter(
                Q(username__icontains=query) |
                Q(name__icontains=query) |
                Q(email__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'usuarios'
        context['placeholder'] = 'Buscar por usuario, nombre o correo'
        return context


@login_required(login_url='login')
def user_create(request):
    if not is_admin(request.user):
        messages.error(request, 'No tienes permisos para crear usuarios.')
        return redirect('home')

    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST, admin_user=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            if request.user.company_id:
                user.company = request.user.company
            user.save()
            messages.success(request, 'Usuario creado correctamente.')
            return redirect('user_list')
    else:
        form = AdminUserCreateForm(admin_user=request.user)

    return render(request, 'core/user/user_form.html', {'form': form, 'title': 'Nuevo usuario'})


@login_required(login_url='login')
def user_update(request, pk):
    if not is_admin(request.user):
        messages.error(request, 'No tienes permisos para editar usuarios.')
        return redirect('home')

    user_model = get_user_model()
    queryset = user_model.objects.exclude(role='SUPERADMIN')
    if request.user.company_id:
        queryset = queryset.filter(company=request.user.company)

    target_user = get_object_or_404(queryset, pk=pk)

    if request.method == 'POST':
        form = AdminUserUpdateForm(request.POST, instance=target_user, admin_user=request.user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            if request.user.company_id:
                updated_user.company = request.user.company
            updated_user.save()
            messages.success(request, 'Usuario actualizado correctamente.')
            return redirect('user_list')
    else:
        form = AdminUserUpdateForm(instance=target_user, admin_user=request.user)

    return render(request, 'core/user/user_form.html', {'form': form, 'title': 'Editar usuario', 'target_user': target_user})


@login_required(login_url='login')
def user_status(request, pk):
    if not is_admin(request.user):
        messages.error(request, 'No tienes permisos para cambiar el estado de usuarios.')
        return redirect('home')

    user_model = get_user_model()
    queryset = user_model.objects.exclude(role='SUPERADMIN')
    if request.user.company_id:
        queryset = queryset.filter(company=request.user.company)

    target_user = get_object_or_404(queryset, pk=pk)

    if target_user.pk == request.user.pk:
        messages.warning(request, 'No puedes desactivar tu propio usuario.')
        return redirect('user_list')

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])
    estado = 'activado' if target_user.is_active else 'desactivado'
    messages.success(request, f'Usuario {target_user.username} {estado} correctamente.')
    return redirect('user_list')

# PRODUCTO
@login_required(login_url='login')
def product_detail(request, id):
    producto = Producto.objects.get(id=id)
    price_history = producto.price_history.all().order_by('-created_at')
    warehouse_stocks = producto.warehouse_stocks.select_related('warehouse').order_by('warehouse__name')
    company_config = (request.user.company.product_custom_fields_config if request.user.company else {}) or {}
    custom_attributes_display = ProductCustomAttributes.build_display_values(company_config, producto.custom_attributes or {})
    
    title = 'Detalle de producto'
    context = {
        'producto': producto, 
        'title': title,
        'price_history': price_history,
        'warehouse_stocks': warehouse_stocks,
        'custom_attributes_display': custom_attributes_display,
    }
    return render(request, 'core/product/product_detail.html', context)

@login_required(login_url='login')
def producto_new(request):
    form = ProductoForm(company=request.user.company)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, company=request.user.company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto creado correctamente.')
            return redirect('product_list')
    title = 'Nuevo producto'
    context = {'form': form, 'title': title}
    return render(request, 'core/product/producto_new.html', context)  

@login_required(login_url='login')
def product_edit(request, id):
    title = 'Editar producto'
    producto = get_object_or_404(Producto, pk=id)
    is_admin_role = getattr(request.user, 'is_admin', False)
    old_price = producto.precio
    active_warehouse = default_user_warehouse(request.user)

    warehouse_location = ''
    if active_warehouse:
        warehouse_stock = ProductStock.objects.filter(product=producto, warehouse=active_warehouse).first()
        if warehouse_stock:
            warehouse_location = warehouse_stock.location or ''

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto, company=request.user.company)
        # Bloquear el campo de costo al editar
        form.fields['cost'].disabled = True
        if is_admin_role:
            if form.is_valid():
                location_value = (form.cleaned_data.get('location') or '').strip()
                original_global_location = producto.location
                producto = form.save(commit=False)
                # Mantener ubicación global legacy sin sobrescribirla desde este formulario.
                producto.location = original_global_location
                
                if 'precio' in form.changed_data:
                    
                    new_price = form.cleaned_data['precio']

                    PriceEvaluationService.propose_new_price(
                        product=producto,
                        old_price=old_price,
                        new_price=new_price,
                        cost_reference=producto.cost,
                        user=request.user,
                        reason="Edición manual por administrador",
                        change_type='MANUAL'
                    )

                    # Mantener precio anterior hasta aprobación
                    producto.precio = old_price
                
                producto.save()

                if active_warehouse:
                    stock_record, _ = ProductStock.objects.get_or_create(
                        product=producto,
                        warehouse=active_warehouse,
                        defaults={'quantity': 0, 'location': location_value},
                    )
                    if stock_record.location != location_value:
                        stock_record.location = location_value
                        stock_record.save(update_fields=['location'])

                messages.success(request, 'Producto actualizado correctamente.')
                return redirect('product_list')
        else:
            messages.error(request, 'No tienes permisos para editar este producto.')
            return redirect('product_list')
    else:
        form = ProductoForm(instance=producto, company=request.user.company)
        # Bloquear el campo de costo al editar
        form.fields['cost'].disabled = True
        form.initial['location'] = warehouse_location
    
    return render(request, 'core/product/producto_new.html', {'form': form, 'title': title})


@login_required(login_url='login')
def product_detail_api(request, id):
    producto = get_object_or_404(Producto, pk=id)
    image_url = producto.imagen.url if producto.imagen else static('img/no-image.png')
    brand = producto.brand.initials if producto.brand else ''

    stock_rows = producto.warehouse_stocks.select_related('warehouse').values(
        'warehouse_id',
        'quantity',
        'location',
    )
    stock_by_warehouse_id = {
        row['warehouse_id']: {
            'quantity': row.get('quantity') or 0,
            'location': row.get('location') or '',
        }
        for row in stock_rows
    }

    warehouse_stocks = []
    for warehouse in accessible_warehouses(request.user):
        row = stock_by_warehouse_id.get(warehouse.id, {'quantity': 0, 'location': ''})
        warehouse_stocks.append({
            'warehouse__name': warehouse.name,
            'quantity': row['quantity'],
            'location': row['location'],
        })

    return JsonResponse({
        'id': producto.id,
        'codigo': producto.nombre,
        'nombre': producto.nombre,
        'descripcion': producto.descripcion or '',
        'marca': brand,
        'precio': str(producto.precio),
        'stock': producto.stock or 0,
        'ubicacion': producto.location or '',
        'warehouse_stocks': warehouse_stocks,
        'imagen': image_url,
    })

class ProductListView(LoginRequiredMixin, ListView):   
    model = Producto
    template_name = 'core/product/productos_list.html'  # Nombre de la plantilla
    context_object_name = 'productos'
    context_title = 'Listado de productos'
    paginate_by = 10  # Número de productos por página
    login_url = 'login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'productos'
        context['placeholder'] = 'Buscar por código, referencia cruzada o descripción'
        custom_config = {}
        if self.request.user.company:
            custom_config = self.request.user.company.product_custom_fields_config or {}

        context['show_custom_attributes'] = bool(custom_config)
        context['custom_attribute_columns'] = [
            {
                'key': key,
                'label': field_cfg.get('label', key.replace('_', ' ').title()) if isinstance(field_cfg, dict) else key,
            }
            for key, field_cfg in custom_config.items()
        ]
        return context
       
    def get_queryset(self):
        query = self.request.GET.get('q')
        object_list = Producto.objects.all().order_by('id')

        selected_warehouse = default_user_warehouse(self.request.user)
        if selected_warehouse:
            location_subquery = ProductStock.objects.filter(
                product=OuterRef('pk'),
                warehouse=selected_warehouse,
            ).values('location')[:1]
            object_list = object_list.annotate(
                report_location=Coalesce(
                    Subquery(location_subquery),
                    Value('', output_field=CharField()),
                )
            )
        else:
            object_list = object_list.annotate(
                report_location=Value('', output_field=CharField())
            )

        if query:
            palabras = [p.strip() for p in query.split('%') if p.strip()]
            for palabra in palabras:
                object_list = object_list.filter(
                    Q(nombre__icontains=palabra)
                    | Q(referencia_cruzada__icontains=palabra)
                    | Q(descripcion__icontains=palabra)
                )
        return object_list


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_admin', False))
def product_catalog_import(request):
    form = ProductCatalogImportForm()

    if request.method == 'POST':
        form = ProductCatalogImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                result = ProductCatalogImportService.import_from_excel(form.cleaned_data['file'])

                summary = (
                    f"Importación completada. "
                    f"Filas válidas: {result['total_rows']} | "
                    f"Creados: {result['created']} | "
                    f"Ya existentes: {result['skipped_existing']} | "
                    f"Duplicados en archivo: {result['duplicate_in_file']}"
                )
                messages.success(request, summary)

                for err in result.get('errors', []):
                    messages.warning(request, err)

                return redirect('product_list')
            except ValueError as e:
                messages.error(request, str(e))

    context = {
        'title': 'Importar catálogo de productos',
        'form': form,
    }
    return render(request, 'core/product/product_catalog_import.html', context)


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_admin', False))
def download_product_catalog_template(request):
    template_bytes = ProductCatalogImportService.build_template_file()
    response = HttpResponse(
        template_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="plantilla_catalogo_productos.xlsx"'
    return response

@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_admin', False))
def cloud_catalog_list(request):
    """Muestra los catálogos disponibles en el repositorio de la nube."""
    company = getattr(request.user, 'company', None)
    if not company or not getattr(company, 'enable_cloud_catalog', False):
        messages.error(request, 'El catálogo nube está deshabilitado para tu empresa.')
        return redirect('product_list')

    try:
        catalogs = ProductCatalogImportService.fetch_cloud_index()
        error = None
    except ValueError as exc:
        catalogs = []
        error = str(exc)

    return render(request, 'core/product/cloud_catalog_list.html', {
        'title': 'Catálogos disponibles en la nube',
        'catalogs': catalogs,
        'error': error,
    })


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_admin', False))
def cloud_catalog_import_from_url(request):
    """Descarga e importa el catálogo seleccionado desde la nube."""
    company = getattr(request.user, 'company', None)
    if not company or not getattr(company, 'enable_cloud_catalog', False):
        messages.error(request, 'El catálogo nube está deshabilitado para tu empresa.')
        return redirect('product_list')

    if request.method != 'POST':
        return redirect('cloud_catalog_list')

    url = request.POST.get('url', '').strip()
    checksum = request.POST.get('checksum', '').strip()
    catalog_name = request.POST.get('catalog_name', 'Catálogo').strip()

    if not url:
        messages.error(request, 'URL del catálogo no proporcionada.')
        return redirect('cloud_catalog_list')

    try:
        result = ProductCatalogImportService.import_from_cloud_url(url, checksum)

        summary = (
            f"Catálogo '{catalog_name}' importado. "
            f"Filas válidas: {result['total_rows']} | "
            f"Creados: {result['created']} | "
            f"Ya existentes: {result['skipped_existing']} | "
            f"Duplicados en archivo: {result['duplicate_in_file']}"
        )
        messages.success(request, summary)

        for err in result.get('errors', []):
            messages.warning(request, err)

    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('product_list')


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_superadmin', False))
def superadmin_cloud_catalog_upload(request):
    """Permite al superadmin subir archivos xlsx al repositorio local de catálogos."""
    if request.method == 'POST':
        form = CloudCatalogUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                catalog = ProductCatalogImportService.save_cloud_catalog(
                    uploaded_file=form.cleaned_data['file'],
                    catalog_name=form.cleaned_data['name'],
                    version=form.cleaned_data['version'],
                )
                if form.cleaned_data.get('publish_now'):
                    ProductCatalogImportService.publish_cloud_catalog(catalog)
                    messages.success(
                        request,
                        f"Catálogo '{catalog['name']}' guardado y publicado correctamente en GitHub.",
                    )
                else:
                    messages.success(
                        request,
                        f"Catálogo '{catalog['name']}' guardado correctamente. Pendiente de publicación manual en GitHub.",
                    )
                return redirect('superadmin_cloud_catalog_upload')
            except ValueError as exc:
                messages.error(request, str(exc))
    else:
        form = CloudCatalogUploadForm()

    context = {
        'title': 'Subir catálogos a la nube',
        'form': form,
        'catalogs': ProductCatalogImportService.get_local_cloud_catalogs(),
        'autopublish_enabled': getattr(settings, 'CLOUD_CATALOG_GIT_AUTOPUBLISH', False),
    }
    return render(request, 'core/catalog/cloud_catalog_upload.html', context)


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_superadmin', False))
def superadmin_cloud_catalog_rename(request):
    if request.method != 'POST':
        return redirect('superadmin_cloud_catalog_upload')

    slug = (request.POST.get('slug') or '').strip()
    new_name = (request.POST.get('name') or '').strip()
    publish_now = request.POST.get('publish_now') == 'on'
    autopublish_enabled = getattr(settings, 'CLOUD_CATALOG_GIT_AUTOPUBLISH', False)

    try:
        updated_catalog = ProductCatalogImportService.rename_cloud_catalog(slug=slug, new_name=new_name)
        if autopublish_enabled and publish_now:
            ProductCatalogImportService.publish_cloud_catalog_index_changes(
                commit_message=f"Rename catalog {updated_catalog['slug']}"
            )
            messages.success(
                request,
                f"Catálogo '{updated_catalog['name']}' actualizado y publicado correctamente en GitHub.",
            )
        else:
            messages.success(request, f"Catálogo '{updated_catalog['name']}' actualizado correctamente.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('superadmin_cloud_catalog_upload')


@login_required(login_url='login')
@user_passes_test(lambda user: getattr(user, 'is_superadmin', False))
def superadmin_cloud_catalog_delete(request):
    if request.method != 'POST':
        return redirect('superadmin_cloud_catalog_upload')

    slug = (request.POST.get('slug') or '').strip()
    publish_now = request.POST.get('publish_now') == 'on'
    autopublish_enabled = getattr(settings, 'CLOUD_CATALOG_GIT_AUTOPUBLISH', False)

    try:
        result = ProductCatalogImportService.delete_cloud_catalog(slug=slug)
        deleted_catalog = result['catalog']
        deleted_file_path = result.get('deleted_file_path')

        if autopublish_enabled and publish_now:
            ProductCatalogImportService.publish_cloud_catalog_delete(
                deleted_file_path=deleted_file_path,
                commit_message=f"Delete catalog {deleted_catalog['slug']}",
            )
            messages.success(
                request,
                f"Catálogo '{deleted_catalog['name']}' eliminado y publicado correctamente en GitHub.",
            )
        else:
            messages.success(request, f"Catálogo '{deleted_catalog['name']}' eliminado correctamente.")
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('superadmin_cloud_catalog_upload')


def is_admin(user):
    try:
        return getattr(user, 'is_admin', False)
    except Exception:
        return False


def _apply_exchange_rate_snapshot(proforma):
    if proforma.exchange_rate_applied:
        return

    company = proforma.company or getattr(proforma.usuario, 'company', None)
    proforma_date = timezone.localtime(proforma.fecha).date() if proforma.fecha else timezone.now().date()

    if not company:
        proforma.currency_source = PROFORMA_BASE_CURRENCY
        proforma.currency_target = PROFORMA_REFERENCE_CURRENCY
        proforma.exchange_rate_applied = DEFAULT_USD_BOB_RATE
        proforma.exchange_rate_date = proforma_date
        return

    target_currency = PROFORMA_REFERENCE_CURRENCY
    source_currency = PROFORMA_BASE_CURRENCY

    if source_currency == target_currency:
        proforma.currency_source = source_currency
        proforma.currency_target = target_currency
        proforma.exchange_rate_applied = Decimal('1.000000')
        proforma.exchange_rate_date = proforma_date
        return

    rate = ExchangeRate.objects.filter(
        company=company,
        from_currency=source_currency,
        to_currency=target_currency,
        is_active=True,
        valid_from__lte=proforma_date,
    ).order_by('-valid_from', '-created_at').first()

    if rate:
        proforma.currency_source = rate.from_currency
        proforma.currency_target = rate.to_currency
        proforma.exchange_rate_applied = rate.rate
        proforma.exchange_rate_date = rate.valid_from
        return

    # Fallback seguro por defecto si no existe tasa configurada para la fecha.
    proforma.currency_source = target_currency
    proforma.currency_target = target_currency
    proforma.exchange_rate_applied = DEFAULT_USD_BOB_RATE
    proforma.exchange_rate_date = proforma_date


def _refresh_exchange_rate_to_active(proforma):
    """Actualiza el tipo de cambio de la proforma al activo en la fecha actual. Solo para proformas no ejecutadas."""
    if proforma.estado == 'EJECUTADO':
        return

    company = proforma.company or getattr(proforma.usuario, 'company', None)
    today = timezone.now().date()

    if not company:
        proforma.currency_source = PROFORMA_BASE_CURRENCY
        proforma.currency_target = PROFORMA_REFERENCE_CURRENCY
        proforma.exchange_rate_applied = DEFAULT_USD_BOB_RATE
        proforma.exchange_rate_date = today
        proforma.save(update_fields=['currency_source', 'currency_target', 'exchange_rate_applied', 'exchange_rate_date'])
        return

    source_currency = PROFORMA_BASE_CURRENCY
    target_currency = PROFORMA_REFERENCE_CURRENCY

    if source_currency == target_currency:
        proforma.currency_source = source_currency
        proforma.currency_target = target_currency
        proforma.exchange_rate_applied = Decimal('1.000000')
        proforma.exchange_rate_date = today
        proforma.save(update_fields=['currency_source', 'currency_target', 'exchange_rate_applied', 'exchange_rate_date'])
        return

    rate = ExchangeRate.objects.filter(
        company=company,
        from_currency=source_currency,
        to_currency=target_currency,
        is_active=True,
        valid_from__lte=today,
    ).order_by('-valid_from', '-created_at').first()

    if rate:
        proforma.currency_source = rate.from_currency
        proforma.currency_target = rate.to_currency
        proforma.exchange_rate_applied = rate.rate
        proforma.exchange_rate_date = rate.valid_from
        proforma.save(update_fields=['currency_source', 'currency_target', 'exchange_rate_applied', 'exchange_rate_date'])
        return

    # Fallback
    proforma.currency_source = target_currency
    proforma.currency_target = target_currency
    proforma.exchange_rate_applied = DEFAULT_USD_BOB_RATE
    proforma.exchange_rate_date = today
    proforma.save(update_fields=['currency_source', 'currency_target', 'exchange_rate_applied', 'exchange_rate_date'])


def _get_exchange_rate_preview(proforma):
    """Calcula el tipo de cambio visible en pantalla sin persistir snapshot."""
    proforma_date = timezone.localtime(proforma.fecha).date() if proforma.fecha else timezone.now().date()
    company = proforma.company or getattr(proforma.usuario, 'company', None)

    # Si ya existe snapshot (proforma ejecutada), mostrar ese valor congelado.
    if proforma.exchange_rate_applied:
        rate_value = Decimal(proforma.exchange_rate_applied)
        return {
            'source_currency': proforma.currency_source or PROFORMA_BASE_CURRENCY,
            'target_currency': proforma.currency_target or PROFORMA_REFERENCE_CURRENCY,
            'rate': rate_value,
            'rate_date': proforma.exchange_rate_date or proforma_date,
            'is_snapshot': True,
            'has_active_rate': True,
            'converted_total': proforma.total_convertido(),
        }

    if not company:
        fallback_rate = DEFAULT_USD_BOB_RATE
        return {
            'source_currency': PROFORMA_BASE_CURRENCY,
            'target_currency': PROFORMA_REFERENCE_CURRENCY,
            'rate': fallback_rate,
            'rate_date': proforma_date,
            'is_snapshot': False,
            'has_active_rate': False,
            'converted_total': proforma.total_neto(),
        }

    source_currency = PROFORMA_BASE_CURRENCY
    target_currency = PROFORMA_REFERENCE_CURRENCY

    if source_currency == target_currency:
        unit_rate = Decimal('1.000000')
        return {
            'source_currency': source_currency,
            'target_currency': target_currency,
            'rate': unit_rate,
            'rate_date': proforma_date,
            'is_snapshot': False,
            'has_active_rate': True,
            'converted_total': proforma.total_neto(),
        }

    current_rate = ExchangeRate.objects.filter(
        company=company,
        from_currency=source_currency,
        to_currency=target_currency,
        is_active=True,
        valid_from__lte=proforma_date,
    ).order_by('-valid_from', '-created_at').first()

    if current_rate:
        proforma.exchange_rate_applied = current_rate.rate
        return {
            'source_currency': current_rate.from_currency,
            'target_currency': current_rate.to_currency,
            'rate': current_rate.rate,
            'rate_date': current_rate.valid_from,
            'is_snapshot': False,
            'has_active_rate': True,
            'converted_total': proforma.total_convertido(),
        }

    fallback_rate = DEFAULT_USD_BOB_RATE
    proforma.exchange_rate_applied = fallback_rate
    return {
        'source_currency': target_currency,
        'target_currency': target_currency,
        'rate': fallback_rate,
        'rate_date': proforma_date,
        'is_snapshot': False,
        'has_active_rate': False,
        'converted_total': proforma.total_convertido(),
    }

@login_required(login_url='login')
@user_passes_test(is_admin)
def approve_price(request, ph_id):
    ph = get_object_or_404(ProductPriceHistory, id=ph_id)

    try:
        PriceApprovalService.approve(ph, approved_by=request.user)
        messages.success(request, f"Precio para {ph.product.nombre} aprobado correctamente.")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('product_detail', id=ph.product.id)

#REJECTED
@login_required(login_url='login')
@user_passes_test(is_admin)
def reject_price(request, ph_id):
    ph = get_object_or_404(ProductPriceHistory, id=ph_id)
    try:
        PriceApprovalService.reject(ph, rejected_by=request.user)
        messages.success(request, f"Precio para {ph.product.nombre} rechazado correctamente.")
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('product_detail', id=ph.product.id)




# PROFORMA
class ProformaListView(ListView):
    model = Proforma
    template_name = 'core/proforma/proformas_list.html'  # Nombre de la plantilla
    context_object_name = 'proformas'
    context_title = 'Listado de proformas'
    paginate_by = 10  # Número de proformas por página

    def get_queryset(self):
        query = self.request.GET.get('q')
        tipo = self.request.GET.get('tipo_busqueda', 'id')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        warehouse_id = self.request.GET.get('warehouse_id')
        if not warehouse_id:
            default_warehouse = default_user_warehouse(self.request.user)
            if default_warehouse:
                warehouse_id = str(default_warehouse.id)

        qs = Proforma.objects.order_by('-fecha')
        
        # 🔹 FILTRO POR USUARIO
        usuario_id = self.request.GET.get("usuario")
        if usuario_id:
            qs = qs.filter(usuario__id=usuario_id)

        # 🔹 FILTRO POR ALMACÉN
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)

        # 🔹 FILTRO POR RANGO DE FECHAS
        fecha_inicio_obj = None
        fecha_fin_obj = None

        # Convertir fecha_inicio
        if fecha_inicio:
            try:
                fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            except ValueError:
                messages.error(self.request, "Fecha inicio inválida.")

        # Convertir fecha_fin
        if fecha_fin:
            try:
                fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            except ValueError:
                messages.error(self.request, "Fecha fin inválida.")

        # Validar rango solo si ambas existen
        if fecha_inicio_obj and fecha_fin_obj:
            if fecha_inicio_obj > fecha_fin_obj:
                messages.error(self.request, "La fecha inicio no puede ser mayor a la fecha fin.")
            else:
                qs = qs.filter(fecha__date__range=(fecha_inicio_obj, fecha_fin_obj))

        # Si solo viene una de las dos
        elif fecha_inicio_obj:
            qs = qs.filter(fecha__date__gte=fecha_inicio_obj)

        elif fecha_fin_obj:
            qs = qs.filter(fecha__date__lte=fecha_fin_obj)

        # 🔹 FILTRO POR BÚSQUEDA
        if query:
            if tipo == 'id':
                if query.isdigit():
                    qs = qs.filter(id=int(query))
                else:
                    messages.error(self.request, 'El ID debe ser un número entero.')

            elif tipo == 'cliente':
                qs = qs.filter(cliente__name__icontains=query)

            elif tipo == 'producto':
                qs = qs.filter(detalles__producto__nombre__icontains=query)

        return qs.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        User = get_user_model()
        context["usuarios"] = User.objects.filter(is_superuser=False)
        context["warehouses"] = accessible_warehouses(self.request.user)
        selected_warehouse_id = self.request.GET.get('warehouse_id')
        if not selected_warehouse_id:
            default_warehouse = default_user_warehouse(self.request.user)
            if default_warehouse:
                selected_warehouse_id = str(default_warehouse.id)
        context["selected_warehouse_id"] = selected_warehouse_id or ''

        # 🔹 Copiar parámetros GET sin page
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context["query_params"] = query_params.urlencode()

        return context


def _get_recommended_products(proforma, query=None, tipo_busqueda='codigo', limit=5):
    max_pending_fallback = 2

    current_product_ids = list(
        Detalle.objects.filter(proforma=proforma).values_list('producto_id', flat=True).distinct()
    )

    # Recomendación basada en productos vendidos junto con los ya cargados en la proforma actual.
    if not current_product_ids:
        return []

    def get_candidate_proformas(states):
        qs = Proforma.objects.filter(estado__in=states)

        if proforma.company_id:
            qs = qs.filter(company_id=proforma.company_id)

        if proforma.pk:
            qs = qs.exclude(id=proforma.pk)

        return qs.filter(detalles__producto_id__in=current_product_ids).distinct()

    def rank_products(source_proformas, excluded_product_ids, take):
        if take <= 0:
            return []

        details = Detalle.objects.filter(proforma__in=source_proformas).exclude(
            producto_id__in=excluded_product_ids
        )

        if query:
            if tipo_busqueda == 'id_producto':
                if not query.isdigit():
                    return []
                details = details.filter(producto_id=int(query))
            else:
                palabras = [p.strip() for p in query.split('%') if p.strip()]
                for palabra in palabras:
                    details = details.filter(
                        Q(producto__nombre__icontains=palabra) |
                        Q(producto__referencia_cruzada__icontains=palabra) |
                        Q(producto__descripcion__icontains=palabra)
                    )

        ranked = details.values('producto_id').annotate(
            co_sold_times=Count('proforma_id', distinct=True),
            total_quantity=Sum('cantidad'),
            last_used=Max('proforma__fecha'),
        ).order_by(
            '-co_sold_times',
            '-total_quantity',
            '-last_used',
        )

        return list(ranked.values_list('producto_id', flat=True)[:take])

    executed_ids = rank_products(
        get_candidate_proformas(['EJECUTADO']),
        excluded_product_ids=current_product_ids,
        take=limit,
    )

    missing = limit - len(executed_ids)
    pending_ids = []
    if missing > 0:
        pending_take = min(missing, max_pending_fallback)
        pending_ids = rank_products(
            get_candidate_proformas(['PENDIENTE']),
            excluded_product_ids=current_product_ids + executed_ids,
            take=pending_take,
        )

    product_ids = executed_ids + pending_ids
    products_by_id = Producto.objects.select_related('brand').in_bulk(product_ids)

    return [products_by_id[product_id] for product_id in product_ids if product_id in products_by_id]

def _get_proforma_context(proforma, request):
    """Helper para obtener el contexto común de proforma_new y proforma_edit"""
    detalles = Detalle.productos_list(proforma)
    productos_list = Producto.objects.none()
    recommended_products = []
    
    query = request.GET.get('q')
    tipo_busqueda = request.GET.get('tipo_busqueda', 'codigo')
    
    if query:
        productos_list = Producto.objects.all()
        if tipo_busqueda == 'id_producto':
            if query.isdigit():
                productos_list = productos_list.filter(id=query)
            else:
                productos_list = Producto.objects.none()
                messages.error(request, 'El ID del producto debe ser un número entero.')
        else:
            palabras = [p.strip() for p in query.split('%') if p.strip()]
            for palabra in palabras:
                productos_list = productos_list.filter(
                    Q(nombre__icontains=palabra)
                    | Q(referencia_cruzada__icontains=palabra)
                    | Q(descripcion__icontains=palabra)
                )

    warehouse_stock_filter = Q(warehouse_stocks__warehouse=proforma.warehouse)
    productos_list = productos_list.annotate(
        warehouse_quantity=Coalesce(
            Sum('warehouse_stocks__quantity', filter=warehouse_stock_filter),
            Value(0),
            output_field=IntegerField(),
        )
    )
    
    paginator = Paginator(productos_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Solo obtener kits si la empresa tiene habilitado el uso de kits
    kits = ProductKit.objects.none()
    enable_kits = False
    if request.user.company and request.user.company.enable_product_kits:
        kits = ProductKit.objects.filter(company=request.user.company, is_active=True)
        enable_kits = True

    enable_product_recommendations = False
    if request.user.company and request.user.company.enable_product_recommendations:
        recommended_products = _get_recommended_products(
            proforma,
            query=query,
            tipo_busqueda=tipo_busqueda,
        )
        recommended_product_ids = [product.id for product in recommended_products]
        recommended_by_id = Producto.objects.filter(id__in=recommended_product_ids).annotate(
            warehouse_quantity=Coalesce(
                Sum('warehouse_stocks__quantity', filter=warehouse_stock_filter),
                Value(0),
                output_field=IntegerField(),
            )
        ).in_bulk()
        recommended_products = [
            recommended_by_id[product_id]
            for product_id in recommended_product_ids
            if product_id in recommended_by_id
        ]
        enable_product_recommendations = True

    exchange_rate_info = _get_exchange_rate_preview(proforma)

    return {
        'proforma': proforma,
        'warehouses': accessible_warehouses(request.user),
        'productos_list': page_obj,
        'detalles': detalles,
        'page_obj': page_obj,
        'tipo_busqueda': tipo_busqueda,
        'kits': kits,
        'enable_kits': enable_kits,
        'recommended_products': recommended_products,
        'enable_product_recommendations': enable_product_recommendations,
        'exchange_rate_info': exchange_rate_info,
    }

@login_required(login_url='login')
def proforma_new(request):
    # Verificar si la última proforma creada no tiene productos
    last_proforma = Proforma.objects.filter(usuario=request.user).last()
    if last_proforma and Detalle.productos_list(last_proforma).count() < 1:
        proforma = last_proforma
        if not proforma.company and request.user.company:
            proforma.company = request.user.company
        if not proforma.warehouse_id:
            proforma.warehouse = default_user_warehouse(request.user)
        proforma.save(update_fields=['company', 'warehouse'])
    else:
        proforma = Proforma.objects.create(
            usuario=request.user,
            warehouse=default_user_warehouse(request.user),
        )
    
    context = _get_proforma_context(proforma, request)
    return render(request, 'core/proforma/proforma_new.html', context)

@login_required(login_url='login')
def proforma_edit(request, id):
    proforma = Proforma.objects.get(id=id)
    update_fields = []

    if not proforma.company and request.user.company:
        proforma.company = request.user.company
        update_fields.append('company')

    should_sync_warehouse = proforma.estado != 'EJECUTADO'
    if should_sync_warehouse:
        try:
            # Valida que el almacén actual sea accesible para el usuario activo.
            if proforma.warehouse_id:
                resolve_user_warehouse(request.user, proforma.warehouse_id)
            warehouse_mismatch = proforma.usuario_id != request.user.id
        except WarehouseAccessDenied:
            warehouse_mismatch = True

        if not proforma.warehouse_id or warehouse_mismatch:
            current_default_warehouse = default_user_warehouse(request.user)
            if proforma.warehouse_id != getattr(current_default_warehouse, 'id', None):
                proforma.warehouse = current_default_warehouse
                update_fields.append('warehouse')

    if update_fields:
        proforma.save(update_fields=update_fields)

    _refresh_exchange_rate_to_active(proforma)
    context = _get_proforma_context(proforma, request)
    return render(request, 'core/proforma/proforma_new.html', context)


@login_required(login_url='login')
def proforma_set_warehouse(request, id):
    if request.method != 'POST':
        return redirect('proforma_edit', id)

    proforma = get_object_or_404(Proforma, id=id)
    if proforma.estado == 'EJECUTADO':
        messages.warning(request, 'No se puede cambiar el almacén de una proforma ejecutada.')
        return redirect('proforma_edit', id)

    try:
        warehouse = resolve_user_warehouse(request.user, request.POST.get('warehouse_id'))
    except WarehouseAccessDenied as exc:
        messages.error(request, str(exc))
        return redirect('proforma_edit', id)
    proforma.warehouse = warehouse
    proforma.save(update_fields=['warehouse'])
    messages.success(request, f'Almacén de salida actualizado a {warehouse.name}.')
    return redirect('proforma_edit', id)


@login_required(login_url='login')
def proforma_search_clients_json(request, id):
    """Busca clientes activos para selección rápida desde modal en proforma."""
    proforma = get_object_or_404(Proforma, id=id)
    query = (request.GET.get('q') or '').strip()
    page = request.GET.get('page', '1')

    clients_qs = Cliente.objects.filter(status=True).order_by('name')
    if query:
        clients_qs = clients_qs.filter(
            Q(name__icontains=query) |
            Q(nit__icontains=query) |
            Q(phone__icontains=query)
        )

    paginator = Paginator(clients_qs, 5)
    page_obj = paginator.get_page(page)

    clients = [
        {
            'id': client.id,
            'name': client.name,
            'nit': client.nit or '',
            'phone': client.phone or '',
        }
        for client in page_obj.object_list
    ]

    return JsonResponse({
        'success': True,
        'proforma_id': proforma.id,
        'results': clients,
        'pagination': {
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'total_results': paginator.count,
        }
    })


@login_required(login_url='login')
@transaction.atomic
def proforma_set_client_json(request, id):
    """Asigna un cliente existente a la proforma desde modal."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    proforma = get_object_or_404(Proforma, id=id)
    client_id = request.POST.get('cliente_id')

    if not client_id:
        return JsonResponse({'success': False, 'error': 'Debe seleccionar un cliente'}, status=400)

    try:
        client = Cliente.objects.get(id=int(client_id), status=True)
    except (ValueError, Cliente.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Cliente inválido o inactivo'}, status=400)

    proforma.cliente = client
    proforma.save(update_fields=['cliente'])

    return JsonResponse({
        'success': True,
        'client': {
            'id': client.id,
            'name': client.name,
            'nit': client.nit or '',
        }
    })


@login_required(login_url='login')
@transaction.atomic
def proforma_create_client_json(request, id):
    """Crea cliente rápidamente y lo asigna a la proforma."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    proforma = get_object_or_404(Proforma, id=id)
    name = (request.POST.get('name') or '').strip()
    nit = (request.POST.get('nit') or '').strip()
    email = (request.POST.get('email') or '').strip()
    phone = (request.POST.get('phone') or '').strip()
    address = (request.POST.get('address') or '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'El nombre es obligatorio'}, status=400)

    if nit and Cliente.objects.filter(nit__iexact=nit).exists():
        return JsonResponse({'success': False, 'error': 'Ya existe un cliente con este NIT'}, status=400)

    client = Cliente.objects.create(
        name=name,
        nit=nit or None,
        email=email or None,
        phone=phone or None,
        address=address or None,
        status=True,
    )

    proforma.cliente = client
    proforma.save(update_fields=['cliente'])

    return JsonResponse({
        'success': True,
        'client': {
            'id': client.id,
            'name': client.name,
            'nit': client.nit or '',
        }
    }, status=201)

@login_required(login_url='login')
@transaction.atomic
def agregar_producto_a_detalle(request):
    def parse_positive_quantity(raw_value):
        try:
            quantity = int(raw_value)
        except (TypeError, ValueError):
            raise ValueError('No se puede agregar una cantidad menor o igual a 0.')

        if quantity <= 0:
            raise ValueError('No se puede agregar una cantidad menor o igual a 0.')

        return quantity

    def parse_positive_price(raw_value):
        try:
            price = Decimal(str(raw_value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError('No se puede agregar un precio menor o igual a 0.')

        if price <= 0:
            raise ValueError('No se puede agregar un precio menor o igual a 0.')

        return price

    def add_detail_to_proforma(proforma, producto, cantidad, precio):
        subtotal = (Decimal(cantidad) * precio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        detalle = Detalle.objects.create(
            proforma=proforma,
            producto=producto,
            cantidad=cantidad,
            precio_venta=precio,
            subtotal=subtotal,
        )

        proforma.total = (Decimal(proforma.total) + subtotal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        proforma.save(update_fields=['total'])
        _refresh_exchange_rate_to_active(proforma)

        producto.latest_price = precio
        producto.save(update_fields=['latest_price'])

        return detalle

    if request.method != 'POST':
        return render(request, 'core/home.html')

    is_json_request = 'application/json' in (request.content_type or '')

    if is_json_request:
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON inválido.'}, status=400)

        proforma_id = payload.get('proforma_id')
        items = payload.get('items') or []
        tipo_busqueda = payload.get('tipo_busqueda', 'codigo')

        if not proforma_id:
            return JsonResponse({'success': False, 'error': 'Falta la proforma.'}, status=400)

        if not items:
            return JsonResponse({'success': False, 'error': 'No se enviaron productos para agregar.'}, status=400)

        proforma = get_object_or_404(Proforma.objects.select_for_update(), id=proforma_id)
        product_ids = [item.get('producto_id') for item in items if item.get('producto_id')]
        productos = Producto.objects.in_bulk(product_ids)

        try:
            for item in items:
                producto_id = item.get('producto_id')
                producto = productos.get(int(producto_id)) if producto_id is not None else None
                if producto is None:
                    raise ValueError('Uno de los productos seleccionados ya no existe.')

                cantidad = parse_positive_quantity(item.get('cantidad'))
                precio = parse_positive_price(item.get('precio'))
                add_detail_to_proforma(proforma, producto, cantidad, precio)
        except ValueError as exc:
            transaction.set_rollback(True)
            return JsonResponse({'success': False, 'error': str(exc)}, status=400)

        redirect_url = f"{reverse_lazy('proforma_edit', args=[proforma_id])}?tipo_busqueda={tipo_busqueda}"
        return JsonResponse({
            'success': True,
            'added_count': len(items),
            'redirect_url': redirect_url,
        })

    proforma_id = request.POST.get('proforma_id')
    producto_id = request.POST.get('producto_id')
    tipo_busqueda = request.POST.get('tipo_busqueda', 'codigo')

    try:
        cantidad = parse_positive_quantity(request.POST.get('cantidad'))
        precio = parse_positive_price(request.POST.get('precio'))
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))

    proforma = get_object_or_404(Proforma.objects.select_for_update(), id=proforma_id)
    producto = get_object_or_404(Producto, id=producto_id)
    add_detail_to_proforma(proforma, producto, cantidad, precio)

    redirect_url = f"{reverse_lazy('proforma_edit', args=[proforma_id])}?tipo_busqueda={tipo_busqueda}"
    return redirect(redirect_url)

@login_required(login_url='login')
def eliminar_producto_a_detalle(request, id):
    proforma_id = request.GET.get('proforma_id')
    try:
        detalle = Detalle.objects.get(id=id)
    except Detalle.DoesNotExist:
        messages.warning(request, 'El producto ya fue eliminado de la proforma.')
        if proforma_id:
            return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))
        return redirect('proforma_list')

    proforma = detalle.proforma
    proforma.total = (Decimal(proforma.total) - Decimal(detalle.subtotal)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    proforma.save(update_fields=['total'])
    _refresh_exchange_rate_to_active(proforma)
    detalle.delete()
    return redirect(reverse_lazy('proforma_edit', args=[proforma.id]))

@login_required(login_url='login')
@transaction.atomic
def editar_cantidad_detalle(request, detalle_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        cantidad = data.get("cantidad", None)
        precio = data.get("precio", None)

        # Normalizar valores vacíos a None
        if cantidad in ("", "null"):
            cantidad = None
        if precio in ("", "null"):
            precio = None

        # Bloquea filas para evitar condiciones de carrera
        detalle = Detalle.objects.select_for_update().get(id=detalle_id)
        proforma = Proforma.objects.select_for_update().get(id=detalle.proforma.id)

        old_subtotal = Decimal(detalle.subtotal)

        # Validar y asignar cantidad si viene
        if cantidad is not None:
            try:
                nueva_cantidad = int(cantidad)
            except (TypeError, ValueError):
                raise ValueError("Cantidad inválida")
            if nueva_cantidad < 1:
                raise ValueError("La cantidad debe ser >= 1")
            detalle.cantidad = nueva_cantidad

        # Validar y asignar precio si viene
        if precio is not None:
            # limpiar formato: comas a punto, quitar símbolos no numéricos salvo "-" y "."
            precio_str = str(precio).strip().replace(",", ".")
            import re
            precio_str = re.sub(r"[^\d\.\-]", "", precio_str)
            try:
                nuevo_precio = Decimal(precio_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except (InvalidOperation, ValueError):
                raise ValueError("Precio inválido")
            if nuevo_precio <= 0:
                raise ValueError("El precio debe ser > 0")
            detalle.precio_venta = nuevo_precio
            # opcional: actualizar latest_price del producto
            try:
                producto = detalle.producto
                producto.latest_price = nuevo_precio
                producto.save()
            except Exception:
                pass

        # Recalcular subtotal con precisión
        detalle.subtotal = (Decimal(detalle.precio_venta) * Decimal(detalle.cantidad)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        detalle.save()

        # Actualizar total de la proforma (restar viejo subtotal y sumar nuevo)
        proforma.total = (Decimal(proforma.total) - old_subtotal + detalle.subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        proforma.save()
        _refresh_exchange_rate_to_active(proforma)

        return JsonResponse({
            "success": True,
            "nueva_cantidad": detalle.cantidad,
            "nuevo_precio": str(detalle.precio_venta),
            "nuevo_subtotal": str(detalle.subtotal),
            "total": str(proforma.total)
        })
    except Detalle.DoesNotExist:
        return JsonResponse({"success": False, "error": "Detalle no encontrado"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Error en el formato JSON"}, status=400)
    except (ValueError, InvalidOperation) as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@login_required(login_url='login')
@transaction.atomic
def cambiar_estado_proforma(request, id):
    try:
        proforma = Proforma.objects.get(id=id)
        
        # VALIDAR DESCUENTO PORCENTUAL
        if request.POST.get('discount_percentage'):
            try:
                discount = float(request.POST.get('discount_percentage'))
                if discount < 0:
                    messages.error(request, 'El descuento no puede ser negativo.')
                    return redirect('proforma_edit', id)
                if discount > 100:
                    messages.warning(request, 'El descuento no puede ser mayor a 100%.')
                    return redirect('proforma_edit', id)
                proforma.discount_percentage = discount
                proforma.save(update_fields=['discount_percentage'])
            except (ValueError, TypeError):
                messages.error(request, 'El descuento debe ser un número válido.')
                return redirect('proforma_edit', id)
        
        if request.POST.get('observacion') is not None:
            proforma.observacion = request.POST.get('observacion')
            proforma.save(update_fields=['observacion'])
        
        if request.POST.get('estado') == 'EJECUTADO':
            if proforma.cliente:
                if not proforma.warehouse_id:
                    messages.error(request, 'Selecciona un almacén de salida antes de ejecutar la proforma.')
                    return redirect('proforma_edit', id)
                proforma.estado = 'EJECUTADO'
                _apply_exchange_rate_snapshot(proforma)
                from collections import defaultdict
                cantidades_por_producto = defaultdict(int)
                detalles = Detalle.productos_list(proforma)
                for detalle in detalles:
                    cantidades_por_producto[detalle.producto.id] += detalle.cantidad

                # Verificar stock agrupado
                for producto_id, cantidad_total in cantidades_por_producto.items():
                    producto = Producto.objects.get(id=producto_id)
                    warehouse_stock = ProductStock.objects.filter(
                        product=producto,
                        warehouse=proforma.warehouse,
                    ).first()
                    available = warehouse_stock.quantity if warehouse_stock else 0
                    if available < cantidad_total:
                        messages.error(
                            request,
                            f'No hay suficiente stock en {proforma.warehouse.name} para el producto "{producto.nombre}". '
                            f'Disponible: {available}.',
                        )
                        return redirect('proforma_edit', id)

                # Descontar stock agrupado
                for producto_id, cantidad_total in cantidades_por_producto.items():
                    producto = Producto.objects.get(id=producto_id)
                    apply_warehouse_stock_change(producto, proforma.warehouse, -cantidad_total)

                # Crear Movement (egreso)
                proforma_content_type = ContentType.objects.get_for_model(Proforma)
                movement = Movement.objects.create(
                    movement_type='OUT',
                    warehouse=proforma.warehouse,
                    content_type=proforma_content_type,
                    object_id=proforma.id,
                    description=f'Egreso por venta de la proforma #{proforma.id}',
                    user=request.user,
                )

                # Crear MovementItems: uno por cada detalle de la proforma (sin agrupar)
                for detalle in detalles:
                    MovementItem.objects.create(
                        movement=movement,
                        product=detalle.producto,
                        quantity=detalle.cantidad,
                    )

                proforma.save()
                messages.success(request, f'Proforma #{proforma.id} ejecutada correctamente.')
            else:
                messages.error(request, 'Esta proforma no tiene asignado un cliente')
                return redirect('proforma_edit', id)
            return redirect('proforma_list')
        else:
            return redirect(reverse_lazy('proforma_edit', args=[proforma.id]))
    except OperationalError:
        messages.warning(
            request,
            'La base de datos estaba ocupada al guardar la proforma. Intenta nuevamente una sola vez.'
        )
        return redirect('proforma_edit', id)

def proforma_view(request, id):
    proforma = Proforma.objects.get(id=id)
    detalles = Detalle.productos_list(proforma)
    total_descuento = proforma.discount_percentage * proforma.total / 100
    total_neto = proforma.total - total_descuento
    literal = numero_a_literal(total_neto)
    exchange_rate_info = _get_exchange_rate_preview(proforma)

    custom_config = {}
    if proforma.company:
        custom_config = proforma.company.product_custom_fields_config or {}

    custom_attribute_columns = [
        {
            'key': key,
            'label': field_cfg.get('label', key.replace('_', ' ').title()) if isinstance(field_cfg, dict) else key,
        }
        for key, field_cfg in custom_config.items()
    ]

    context = {
        'proforma': proforma,
        'detalles': detalles,
        'total_descuento': total_descuento,
        'total_con_descuento': total_neto,
        'literal': literal,
        'exchange_rate_info': exchange_rate_info,
        'custom_attribute_columns': custom_attribute_columns,
        'detail_table_colspan': 6 + len(custom_attribute_columns),
        'detail_total_blank_colspan': 5 + len(custom_attribute_columns),
    }
    return render(request, 'core/proforma/proforma_view.html', context)

@login_required(login_url='login')
@transaction.atomic
def anular_proforma(request, id):
    proforma = get_object_or_404(Proforma, id=id)

    if proforma.estado != 'EJECUTADO':
        messages.warning(request, 'Solo se pueden anular proformas que ya fueron ejecutadas.')
        return redirect('proforma_edit', id)

    proforma_content_type = ContentType.objects.get_for_model(Proforma)
    sale_movement = Movement.objects.filter(
        content_type=proforma_content_type,
        object_id=proforma.id,
        movement_type='OUT',
    ).first()
    warehouse = sale_movement.warehouse if sale_movement and sale_movement.warehouse_id else proforma.warehouse
    if warehouse is None:
        messages.error(request, 'No se encontró el almacén de salida de esta proforma.')
        return redirect('proforma_edit', id)

    # Cambiar estado a ANULADO
    proforma.estado = 'ANULADO'
    proforma.save(update_fields=['estado'])

    # Revertir el stock (crear ingreso)
    for detalle in Detalle.productos_list(proforma):
        producto = Producto.objects.get(id=detalle.producto.id)
        apply_warehouse_stock_change(producto, warehouse, detalle.cantidad)

    # Crear movimiento tipo INGRESO
    ingreso_movement = Movement.objects.create(
        movement_type='IN',
        warehouse=warehouse,
        content_type=proforma_content_type,
        object_id=proforma.id,
        description=f'Ingreso por anulación de proforma #{proforma.id}',
        user=request.user,
    )

    # Registrar items del ingreso
    for detalle in Detalle.productos_list(proforma):
        producto = Producto.objects.get(id=detalle.producto.id)
        MovementItem.objects.create(
            movement=ingreso_movement,
            product=producto,
            quantity=detalle.cantidad,
        )

    messages.success(request, f'Proforma #{proforma.id} anulada y movimiento revertido.')
    return redirect('proforma_list')    

@login_required
def cambiar_fecha_proforma(request, id):
    proforma = Proforma.objects.get(id=id)

    if proforma.estado == 'EJECUTADO':
        messages.warning(request, 'No se puede cambiar la fecha de una proforma ejecutada.')
        return redirect('proforma_edit', id)

    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        if fecha_str:
            try:
                fecha_naive = datetime.strptime(fecha_str, "%Y-%m-%d")
                proforma.fecha = timezone.make_aware(fecha_naive)
                proforma.save(update_fields=['fecha'])
                messages.success(request, "Fecha actualizada correctamente.")
            except ValueError:
                messages.error(request, 'Fecha inválida.')
    return redirect('proforma_edit', id)

@login_required
@transaction.atomic
def copiar_proforma(request, id):
    """Copia una proforma: mantiene cliente, fecha actual, precio = max(precio_proforma, precio_actual)."""
    origen = get_object_or_404(Proforma, id=id)
    detalles_origen = Detalle.objects.select_related('producto').filter(proforma=origen)

    nueva = Proforma.objects.create(
        usuario=request.user,
        cliente=origen.cliente,
        estado='PENDIENTE',
        # fecha usa default=timezone.now → ya es la fecha actual
    )

    total_nueva = Decimal('0.00')
    for d in detalles_origen:
        precio_usado = max(
            Decimal(d.precio_venta or 0),
            Decimal(d.producto.precio or 0),
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        subtotal = (Decimal(d.cantidad) * precio_usado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        Detalle.objects.create(
            proforma=nueva,
            producto=d.producto,
            cantidad=d.cantidad,
            precio_venta=precio_usado,
            subtotal=subtotal,
        )
        total_nueva += subtotal

    nueva.total = total_nueva
    nueva.save(update_fields=['total'])

    messages.success(request, f'Proforma #{origen.id} copiada como #{nueva.id}.')
    return redirect('proforma_edit', nueva.id)

# CLIENTE    
class ClientListView(ListView):
    model = Cliente
    template_name = 'core/client/client_list.html'  # Nombre de la plantilla
    context_object_name = 'clientes'
    paginate_by = 10  # Número de clientes por página
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'clientes'
        context['placeholder'] = 'Buscar por nombre o NIT'
        return context

    def get_queryset(self):
        query = self.request.GET.get('q')
        object_list = Cliente.objects.all().order_by('name')
        if query:
            object_list = object_list.filter(name__icontains=query) | object_list.filter(nit__icontains=query)
        return object_list

@login_required(login_url='login')
def cliente_new(request):
    form = ClienteForm()
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente creado correctamente.')
            return redirect('client_list')
    title = 'Nuevo Cliente'
    context = {'form': form, 'title': title}
    return render(request, 'core/client/cliente_form.html', context)

@login_required(login_url='login')
def crear_clientes(request):
    fake = Faker()
    for i in range(10):
        name = fake.name()
        nit = fake.bothify(text='########-#')
        email = fake.email()
        phone = fake.phone_number()
        address = fake.address()
        cliente = Cliente(
            name=name,
            nit=nit,
            email=email,
            phone=phone,
            address=address
        )
        cliente.save()
    return redirect('client_list')

@login_required(login_url='login')
def cliente_edit(request, id):
    cliente = get_object_or_404(Cliente, pk=id)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('client_list')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'core/client/cliente_form.html', {'form': form})   

@login_required(login_url='login')
def cliente_delete(request, id):
    cliente = Cliente.objects.get(id=id)
    cliente.delete()
    return redirect('client_list')

@login_required(login_url='login')
def cliente_status(request, id):
    cliente = Cliente.objects.get(pk=id)
    if cliente.status:
        cliente.status = False
        messages.info(request, f'Cliente {cliente.name} desactivado correctamente.')
    else:
        cliente.status = True
        messages.success(request, f'Cliente {cliente.name} activado correctamente.')
    cliente.save()
    return redirect('client_list')

# FUNCIONES

def numero_a_literal(numero):
    entero = int(numero)
    decimal = int((numero - entero) * 100)
    return nl.Numero(entero).a_letras + ' con ' + str(decimal) + '/100'

# Generar proforma en PDF
def generate_proforma_pdf(request, id):
    proforma = Proforma.objects.get(id=id)
    # Datos de ejemplo, puedes obtenerlos de tu base de datos
    literal = numero_a_literal(proforma.total)
    context = {
        'id': proforma.id,
        'cliente': proforma.cliente,
        'fecha': proforma.fecha,        
        'detalles': Detalle.objects.filter(proforma=proforma),
        'total': proforma.total,
        'literal': literal
    }
   
    return render(request, 'core/proforma_pdf.html', context)

# ReportesGenerales
def reportes(request):
    return render(request, 'core/reportes.html')

# PROVEEDOR
class SupplierListView(ListView):
    model = Supplier
    template_name = 'core/supplier/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10
    
    # añadir "title" a context para mostrar en la plantilla
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'proveedores'
        context['placeholder'] = 'Buscar por nombre'
        return context
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        object_list = Supplier.objects.all()
        if query:
            object_list = object_list.filter(name__icontains=query)
        return object_list

def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor creado correctamente.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    title = 'Nuevo Proveedor'
    context = {'form': form, 'title': title}
    return render(request, 'core/supplier/supplier_form.html', context )

def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor actualizado correctamente.')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'core/supplier/supplier_form.html', {'form': form})

# MARCA
class BrandListView(ListView):
    model = Brand
    template_name = 'core/brand/brand_list.html'
    context_object_name = 'brands'
    paginate_by = 10
    
    # añadir "title" a context para mostrar en la plantilla
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'marcas'
        context['placeholder'] = 'Buscar por nombre'
        return context
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        object_list = Brand.objects.all()
        if query:
            object_list = object_list.filter(name__icontains=query)
        return object_list

def brand_create(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            brand_name = form.cleaned_data['name']
            if Brand.objects.filter(name__iexact=brand_name).exists():
                messages.warning(request, f'La marca "{brand_name}" ya existe.')
                return redirect('brand_list')

            form.save()
            messages.success(request, 'Marca creada correctamente.')
            return redirect('brand_list')
    else:
        form = BrandForm()
    title = 'Nueva Marca'
    context = {'form': form, 'title': title}
    return render(request, 'core/brand/brand_form.html', context)

def brand_update(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marca actualizada correctamente.')
            return redirect('brand_list')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'core/brand/brand_form.html', {'form': form})

def brand_status(request, pk):
    brand = Brand.objects.get(pk=pk)
    if brand.status:
        brand.status = False
        messages.info(request, f'Marca {brand.name} desactivada correctamente.')
    else:
        brand.status = True
        messages.success(request, f'Marca {brand.name} activada correctamente.')
    brand.save()
    return redirect('brand_list')

# Reporte PDF de profoma
def _build_insufficient_stock_product_ids(detalles):
    """Retorna IDs de productos cuyo stock es menor al total solicitado en la proforma."""
    from collections import defaultdict

    requested_by_product = defaultdict(int)
    stock_by_product = {}

    for detalle in detalles:
        product_id = detalle.producto.id
        requested_by_product[product_id] += int(detalle.cantidad)
        stock_by_product[product_id] = int(detalle.producto.stock)

    return {
        product_id
        for product_id, requested in requested_by_product.items()
        if stock_by_product.get(product_id, 0) < requested
    }


def proforma_pdf(request, proforma_id):
    proforma = Proforma.objects.get(id=proforma_id)
    detalles = list(Detalle.objects.select_related('producto').filter(proforma=proforma))
    insufficient_stock_product_ids = _build_insufficient_stock_product_ids(detalles)
    
    # Convertimos los valores a Decimal para mayor precisión
    total = Decimal(proforma.total)
    descuento_porcentaje = Decimal(proforma.discount_percentage) / Decimal(100)

    # Calculamos el descuento con precisión
    descuento = (total * descuento_porcentaje).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculamos el total neto
    total_neto = (total - descuento).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    exchange_rate_info = _get_exchange_rate_preview(proforma)
    total_bs = exchange_rate_info['converted_total']
    
    total_literal = numero_a_literal(total_neto)
    company = Company.objects.get(id=proforma.company.id)
    
    logo_url = None
    if company.logo:
        logo_url = request.build_absolute_uri(company.logo.url)
        
    context = {
        'proforma': proforma,
        'detalles': detalles,
        'descuento': descuento,
        'total_neto': total_neto,
        'total_bs': total_bs,
        'exchange_rate_info': exchange_rate_info,
        'total_literal': total_literal,
        'insufficient_stock_product_ids': insufficient_stock_product_ids,
        'logo_url': logo_url,
        'company': company
    }
    
    html_string = render_to_string('core/proforma/proforma_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="proforma_{proforma_id}.pdf"'
    
    pdf = weasyprint.HTML(string=html_string).write_pdf()
    response.write(pdf)
    
    return response

def proforma_almacen(request, proforma_id):
    proforma = Proforma.objects.get(id=proforma_id)
    detalles = list(Detalle.objects.select_related('producto').filter(proforma=proforma))
    insufficient_stock_product_ids = _build_insufficient_stock_product_ids(detalles)
    
    # Convertimos los valores a Decimal para mayor precisión
    total = Decimal(proforma.total)
    descuento_porcentaje = Decimal(proforma.discount_percentage) / Decimal(100)

    # Calculamos el descuento con precisión
    descuento = (total * descuento_porcentaje).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculamos el total neto
    total_neto = (total - descuento).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    exchange_rate_info = _get_exchange_rate_preview(proforma)
    total_bs = exchange_rate_info['converted_total']
    
    total_literal = numero_a_literal(total_neto)
    company = Company.objects.get(id=proforma.company.id)
    
    logo_url = None
    if company.logo:
        logo_url = request.build_absolute_uri(company.logo.url)
        
    context = {
        'proforma': proforma,
        'detalles': detalles,
        'total_bs': total_bs,
        'exchange_rate_info': exchange_rate_info,
        'total_literal': total_literal,
        'insufficient_stock_product_ids': insufficient_stock_product_ids,
        'logo_url': logo_url,
        'company': company
    }
    
    html_string = render_to_string('core/proforma/proforma_almacen.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="proforma_{proforma_id}_code.pdf"'
    
    pdf = weasyprint.HTML(string=html_string).write_pdf()
    response.write(pdf)
    
    return response


# KIT DE PRODUCTOS
class ProductKitListView(LoginRequiredMixin, ListView):
    model = ProductKit
    template_name = 'core/kit/kit_list.html'
    context_object_name = 'kits'
    paginate_by = 10
    login_url = 'login'
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        kits = ProductKit.objects.filter(company=self.request.user.company)
        if query:
            kits = kits.filter(name__icontains=query)
        return kits.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'kits de productos'
        context['placeholder'] = 'Buscar por nombre'
        return context

@login_required(login_url='login')
def kit_create(request):
    if request.method == 'POST':
        form = ProductKitForm(request.POST)
        if form.is_valid():
            kit = form.save(commit=False)
            kit.user = request.user
            kit.company = request.user.company
            kit.save()
            messages.success(request, 'Kit creado correctamente.')
            return redirect('kit_detail', pk=kit.id)
    else:
        form = ProductKitForm()
    
    return render(request, 'core/kit/kit_form.html', {'form': form, 'title': 'Nuevo Kit'})

@login_required(login_url='login')
def kit_detail(request, pk):
    kit = get_object_or_404(ProductKit, pk=pk, company=request.user.company)
    items = kit.items.all()
    
    return render(request, 'core/kit/kit_detail.html', {
        'kit': kit,
        'items': items,
        'title': f'Kit: {kit.name}'
    })

@login_required(login_url='login')
def kit_edit(request, pk):
    kit = get_object_or_404(ProductKit, pk=pk, company=request.user.company)
    
    if request.method == 'POST':
        form = ProductKitForm(request.POST, instance=kit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kit actualizado correctamente.')
            return redirect('kit_detail', pk=kit.id)
    else:
        form = ProductKitForm(instance=kit)
    
    return render(request, 'core/kit/kit_form.html', {'form': form, 'kit': kit, 'title': 'Editar Kit'})

@login_required(login_url='login')
def kit_delete(request, pk):
    if request.method != 'POST':
        messages.error(request, 'Método no permitido.')
        return redirect('kit_list')

    kit = get_object_or_404(ProductKit, pk=pk, company=request.user.company)
    kit.is_active = not kit.is_active
    kit.save()

    if kit.is_active:
        messages.success(request, 'Kit activado correctamente.')
    else:
        messages.success(request, 'Kit desactivado correctamente.')

    return redirect('kit_list')

@login_required(login_url='login')
def kit_add_item(request, pk):
    kit = get_object_or_404(ProductKit, pk=pk, company=request.user.company)
            
    if request.method == 'POST':
        form = ProductKitItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)

            # VALIDACIÓN: el producto debe tener precio de venta > 0 antes de añadirse al kit
            producto = item.producto
            # Intentar campos comunes: 'precio' o 'latest_price'
            price = getattr(producto, 'precio', None)
            if price is None:
                price = getattr(producto, 'latest_price', None)

            try:
                price_value = float(price) if price is not None else 0.0
            except (TypeError, ValueError):
                price_value = 0.0

            if price_value <= 0.0:
                # Añadir error al formulario y volver a renderizar para que el usuario corrija
                form.add_error('producto', 'El producto debe tener un precio de venta válido mayor a 0 antes de añadirlo al kit.')
                return render(request, 'core/kit/kit_item_form.html', {
                    'form': form,
                    'kit': kit,
                    'title': f'Agregar producto a {kit.name}'
                })

            item.kit = kit
            item.save()
            messages.success(request, 'Producto agregado al kit.')
            return redirect('kit_detail', pk=kit.id)
    else:
        form = ProductKitItemForm()
    
    return render(request, 'core/kit/kit_item_form.html', {
        'form': form,
        'kit': kit,
        'title': f'Agregar producto a {kit.name}'
    })

@login_required(login_url='login')
def kit_remove_item(request, pk, item_id):
    kit = get_object_or_404(ProductKit, pk=pk, company=request.user.company)
    item = get_object_or_404(ProductKitItem, pk=item_id, kit=kit)
    item.delete()
    messages.success(request, 'Producto removido del kit.')
    return redirect('kit_detail', pk=kit.id)

# Para obtener kit items via AJAX en proforma
@login_required(login_url='login')
def get_kit_items(request, kit_id):
    """API para obtener items de un kit"""
    kit = get_object_or_404(ProductKit, pk=kit_id, company=request.user.company, is_active=True)
    items = kit.items.all().values(
        'id', 
        'producto__id', 
        'producto__nombre', 
        'producto__descripcion',
        'cantidad', 
        'producto__precio'
    )
    return JsonResponse({'items': list(items)})


@login_required(login_url='login')
def generate_prices_view(request):
    """Genera precios automáticos para productos sin precio.
    
    Parámetros GET:
    - margin: Margen de ganancia (ej: 0.35 = 35%, default 0.35)
    - auto_approve: '1' o 'true' para aprobar automáticamente
    - json: '1' o 'true' para devolver JSON en lugar de redireccionar
    """
    try:
        # Obtener parámetros
        margin_str = request.GET.get('margin', '0.35')
        auto_approve = request.GET.get('auto_approve', '1') in ['1', 'true', 'on']
        return_json = request.GET.get('json', '0') in ['1', 'true', 'on']
        
        # Validar margin
        try:
            margin = Decimal(str(margin_str))
            if margin < 0 or margin > 5:
                raise ValueError("El margen debe estar entre 0 y 5 (0% a 500%)")
        except (ValueError, TypeError):
            raise ValueError(f"Margen inválido: {margin_str}")
        
        # Ejecutar servicio
        result = AutoPriceService.generate_missing_prices(
            margin=margin,
            auto_approve=auto_approve,
            user=request.user
        )
        
        # Preparar resumen
        summary = f"Procesados: {result['total']} | Actualizados: {result['updated']}"
        if result['failed'] > 0:
            summary += f" | Errores: {result['failed']}"
        
        messages.success(request, summary)
        
        # Retornar JSON o redirigir
        if return_json:
            return JsonResponse(result)
        else:
            return redirect('product_list')
            
    except Exception as e:
        error_msg = f"Error al generar precios: {str(e)}"
        messages.error(request, error_msg)
        if request.GET.get('json') in ['1', 'true', 'on']:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        return redirect('product_list')