from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib import messages  # Importa el framework de mensajes
from django.core.paginator import Paginator
from django.views.generic import ListView, UpdateView, TemplateView
from .models import Proforma, Producto, Detalle, Cliente, Supplier, Brand, Company
from .forms import ProductoForm, ClienteForm, ProformaAddClientForm, SupplierForm, BrandForm, \
                    CustomPasswordChangeForm, UserProfileForm

from inv.models import Movement, MovementItem  # Asegúrate de importar tus modelos correctamente
from django.db import transaction
#reporte pdf
#from django.http import HttpResponse
#from django.template.loader import get_template
#from weasyprint import HTML
from nlt import numlet as nl

from faker import Faker

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.contenttypes.models import ContentType

# PDF
import weasyprint
from django.http import HttpResponse
from django.template.loader import render_to_string
from decimal import Decimal, ROUND_HALF_UP

from django.http import JsonResponse
import json

from django.utils.dateparse import parse_date

# Create your views here.

# HOME
@login_required(login_url='login')
def home(request):
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
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed successfully.")
        return super().form_valid(form)

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('home')  # Cambia por tu vista de perfil si la tienes
    else:
        form = UserProfileForm(instance=user)
    
    return render(request, 'core/registration/edit_profile.html', {'form': form})

# PRODUCTO
@login_required(login_url='login')
def product_detail(request, id):
    producto = Producto.objects.get(id=id)
    title = 'Detalle de producto'
    context = {'producto': producto, 'title': title}
    return render(request, 'core/product/product_detail.html', context)

@login_required(login_url='login')
def producto_new(request):
    form = ProductoForm()
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    title = 'Nuevo producto'
    context = {'form': form, 'title': title}
    return render(request, 'core/product/producto_new.html', context)  

@login_required(login_url='login')
def product_edit(request, id):
    title = 'Editar producto'
    producto = get_object_or_404(Producto, pk=id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'core/product/producto_new.html', {'form': form, 'title': title})

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
        context['placeholder'] = 'Buscar por codigo o descripción'
        return context
       
    def get_queryset(self):
        query = self.request.GET.get('q')
        object_list = Producto.objects.all().order_by('nombre')
        if query:
            object_list = object_list.filter(nombre__icontains=query) | object_list.filter(descripcion__icontains=query)
        return object_list

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
        qs = Proforma.objects.order_by('-fecha')
        if query:
            if tipo == 'id':
                qs = qs.filter(id__icontains=query)
            elif tipo == 'cliente':
                qs = qs.filter(cliente__name__icontains=query)
            elif tipo == 'producto':
                qs = qs.filter(detalles__producto__nombre__icontains=query)
        return qs.distinct()

def proforma_new(request):
    query = request.GET.get('q')
    
    # Verificar si la última proforma creada no tiene productos en su detalle
    last_proforma = Proforma.objects.filter(usuario=request.user).last()
    if last_proforma and Detalle.productos_list(last_proforma).count() < 1:
        proforma = last_proforma
    else:
        proforma = Proforma.objects.create(usuario=request.user)
        
    detalles = Detalle.productos_list(proforma)
    productos_list = Producto.objects.all()
        
    if query:
        productos_list = productos_list.filter(nombre__icontains=query)
    
    paginator = Paginator(productos_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'proforma': proforma,
        'productos_list': page_obj,
        'detalles': detalles,
        'page_obj': page_obj
    }

    return render(request, 'core/proforma/proforma_new.html', context)
    
def proforma_add_client(request, id):
    context_title = 'Seleccionar cliente'
    proforma = Proforma.objects.get(id=id)
    if request.method == 'POST':
        form = ProformaAddClientForm(request.POST, instance=proforma)
        if form.is_valid():
            form.save()
            return redirect('proforma_edit', id)
    else:
        # Clientes activos
        clients_list = Cliente.objects.filter(status=True)
        form = ProformaAddClientForm(instance=proforma)
        if query := request.GET.get('q'):
            clients_list = clients_list.filter(name__icontains=query)
            paginator = Paginator(clients_list, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number) 
        else:
            paginator = Paginator(clients_list, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
        context = {
            'form': form,
            'title': context_title,
            'clients_list': page_obj,
            'proforma': proforma, 
            'page_obj': page_obj
        }
            
    return render(request, 'core/proforma/proforma_add_client.html', context)

def proforma_edit(request, id):
    proforma = Proforma.objects.get(id=id)
    detalles = Detalle.productos_list(proforma)
    productos_list = Producto.objects.all()
        
    if query := request.GET.get('q'):
        productos_list = productos_list.filter(nombre__icontains=query)
        paginator = Paginator(productos_list, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {'proforma': proforma, 'productos_list': page_obj, 'detalles': detalles, 'page_obj': page_obj }
    else:
        paginator = Paginator(productos_list, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {'proforma': proforma, 'productos_list': page_obj, 'detalles': detalles, 'page_obj': page_obj }
        
    return render(request, 'core/proforma/proforma_new.html', context)

def agregar_producto_a_detalle(request):
    # VALIR DATOS SI ES POST O GET
    if request.method == 'POST':
        proforma_id = request.POST.get('proforma_id')
        producto_id = request.POST.get('producto_id')
        cantidad = request.POST.get('cantidad')  
        precio = request.POST.get('precio')
        if not cantidad or int(cantidad) <= 0:
            messages.error(request, f'No se puede agregar una cantidad menor o igual a 0.')
            return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))
        if not precio or float(precio) <= 0:
            messages.error(request, f'No se puede agregar un precio menor o igual a 0.')
            return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))
        #añadir a subtotal en float
        subtotal =  float(cantidad) * float(precio)
        
        # CREAR DETALLE
        proforma = Proforma.objects.get(id=proforma_id)
        producto = Producto.objects.get(id=producto_id)
        detalle = Detalle.objects.create(proforma=proforma, producto=producto, cantidad=cantidad, precio_venta=precio , subtotal=subtotal)
        detalle.save()
        # ACTUALIZAR TOTAL DE PROFORMA        
        proforma.total = float(proforma.total) + float(subtotal)
        proforma.save()
        producto.latest_price = precio
        producto.save()
        # REDIRECCIONAR A LA MISMA PAGINA
        return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))
    else:
        return render(request, 'core/home.html')

def eliminar_producto_a_detalle(request, id):
    detalle = Detalle.objects.get(id=id)
    proforma = detalle.proforma
    proforma.total = float(proforma.total) - float(detalle.subtotal)
    proforma.save()
    detalle.delete()
    return redirect(reverse_lazy('proforma_edit', args=[proforma.id]))

@csrf_exempt
def editar_cantidad_detalle(request, detalle_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            nueva_cantidad = int(data.get("cantidad"))

            detalle = Detalle.objects.get(id=detalle_id)
            proforma = Proforma.objects.get(id=detalle.proforma.id)
            proforma.total = proforma.total - detalle.subtotal
            proforma.save()
            detalle.cantidad = nueva_cantidad
            detalle.subtotal = detalle.precio_venta * detalle.cantidad
            detalle.save()
            proforma.total = proforma.total + detalle.subtotal
            proforma.save()
            
            return JsonResponse({"success": True, "nueva_cantidad": nueva_cantidad})
        except Detalle.DoesNotExist:
            return JsonResponse({"success": False, "error": "Detalle no encontrado"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Error en el formato JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    
    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

@transaction.atomic
def cambiar_estado_proforma(request, id):
    proforma = Proforma.objects.get(id=id)
    if request.POST.get('discount_percentage'):
        proforma.discount_percentage = request.POST.get('discount_percentage')
        proforma.save()
    if request.POST.get('observacion'):
        proforma.observacion = request.POST.get('observacion')
        proforma.save()
    if request.POST.get('estado') == 'EJECUTADO':
        if proforma.cliente:    
            proforma.estado = 'EJECUTADO'
            # Verificar si hay suficiente stock para cada producto
            for detalle in Detalle.productos_list(proforma):
                producto = Producto.objects.get(id=detalle.producto.id)
                if producto.stock < detalle.cantidad:
                    messages.error(request, f'No hay suficiente stock para el producto "{producto.nombre}".')
                    return redirect('proforma_edit', id)
            # Actualizar el stock de cada producto
            for detalle in Detalle.productos_list(proforma):
                producto = Producto.objects.get(id=detalle.producto.id)
                producto.stock -= detalle.cantidad
                producto.save()

            # Crear el Movement para la venta (Egreso)
            proforma_content_type = ContentType.objects.get_for_model(Proforma)
            movement = Movement.objects.create(
                movement_type='OUT',
                content_type=proforma_content_type,
                object_id=proforma.id,
                description=f'Egreso por venta de la proforma #{proforma.id}',
                user=request.user,
            )

            # Crear los MovementItems
            for detalle in Detalle.productos_list(proforma):
                producto = Producto.objects.get(id=detalle.producto.id)
                MovementItem.objects.create(
                    movement=movement,
                    product=producto,
                    quantity=detalle.cantidad,
                )

            # Guardar la proforma
            proforma.save()
        else:
            messages.error(request, 'Esta proforma no tiene asignado un cliente')
            return redirect('proforma_edit', id)
        return redirect('proforma_list')
    else:
        return redirect(reverse_lazy('proforma_edit', args=[proforma.id]))

def proforma_view(request, id):
    proforma = Proforma.objects.get(id=id)
    detalles = Detalle.productos_list(proforma)
    total_descuento = proforma.discount_percentage * proforma.total / 100
    total_neto = proforma.total - total_descuento
    literal = numero_a_literal(total_neto)
    context = {
        'proforma': proforma,
        'detalles': detalles,
        'total_descuento': total_descuento,
        'total_con_descuento': total_neto,
        'literal': literal
    }
    return render(request, 'core/proforma/proforma_view.html', context)

@transaction.atomic
def anular_proforma(request, id):
    proforma = get_object_or_404(Proforma, id=id)

    if proforma.estado != 'EJECUTADO':
        messages.warning(request, 'Solo se pueden anular proformas que ya fueron ejecutadas.')
        return redirect('proforma_edit', id)

    # Cambiar estado a ANULADO
    proforma.estado = 'ANULADO'
    proforma.save()

    # Revertir el stock (crear ingreso)
    for detalle in Detalle.productos_list(proforma):
        producto = Producto.objects.get(id=detalle.producto.id)
        producto.stock += detalle.cantidad
        producto.save()

    # Crear movimiento tipo INGRESO
    proforma_content_type = ContentType.objects.get_for_model(Proforma)
    ingreso_movement = Movement.objects.create(
        movement_type='IN',
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
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        if fecha_str:
            # Si tu campo es DateTimeField, puedes hacer:
            from datetime import datetime
            proforma.fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            proforma.save()
            messages.success(request, "Fecha actualizada correctamente.")
    return redirect('proforma_edit', id)

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
    else:
        cliente.status = True
    cliente.save()
    return redirect('client_list')

# FUNCIONES

def numero_a_literal(numero):
    entero = int(numero)
    decimal = int((numero - entero) * 100)
    return nl.Numero(entero).a_letras + ' con ' + str(decimal) + '/100 Dólares'

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
            form.save()
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
            return redirect('brand_list')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'core/brand/brand_form.html', {'form': form})

def brand_status(request, pk):
    brand = Brand.objects.get(pk=pk)
    if brand.status:
        brand.status = False
    else:
        brand.status = True
    brand.save()
    return redirect('brand_list')

# Reporte PDF de profoma
def proforma_pdf(request, proforma_id):
    proforma = Proforma.objects.get(id=proforma_id)
    detalles = Detalle.objects.filter(proforma=proforma)
    
    # Convertimos los valores a Decimal para mayor precisión
    total = Decimal(proforma.total)
    descuento_porcentaje = Decimal(proforma.discount_percentage) / Decimal(100)

    # Calculamos el descuento con precisión
    descuento = (total * descuento_porcentaje).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculamos el total neto
    total_neto = (total - descuento).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Convertimos a bolivianos con precisión
    total_bs = (total_neto * Decimal('6.96')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    total_literal = numero_a_literal(total_neto)
    company = Company.objects.get(id=proforma.usuario.company.id)
    
    logo_url = None
    if proforma.usuario.company.logo:
        logo_url = request.build_absolute_uri(proforma.usuario.company.logo.url)
        
    context = {
        'proforma': proforma,
        'detalles': detalles,
        'descuento': descuento,
        'total_neto': total_neto,
        'total_bs': total_bs,
        'total_literal': total_literal,
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
    detalles = Detalle.objects.filter(proforma=proforma)
    
    # Convertimos los valores a Decimal para mayor precisión
    total = Decimal(proforma.total)
    descuento_porcentaje = Decimal(proforma.discount_percentage) / Decimal(100)

    # Calculamos el descuento con precisión
    descuento = (total * descuento_porcentaje).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Calculamos el total neto
    total_neto = (total - descuento).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Convertimos a bolivianos con precisión
    total_bs = (total_neto * Decimal('6.96')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    total_literal = numero_a_literal(total_neto)
    company = Company.objects.get(id=proforma.usuario.company.id)
    
    logo_url = None
    if proforma.usuario.company.logo:
        logo_url = request.build_absolute_uri(proforma.usuario.company.logo.url)
        
    context = {
        'proforma': proforma,
        'detalles': detalles,
        'total_bs': total_bs,
        'total_literal': total_literal,
        'logo_url': logo_url,
        'company': company
    }
    
    html_string = render_to_string('core/proforma/proforma_almacen.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="proforma_{proforma_id}_code.pdf"'
    
    pdf = weasyprint.HTML(string=html_string).write_pdf()
    response.write(pdf)
    
    return response
