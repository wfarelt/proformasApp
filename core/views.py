from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.views.generic import ListView, UpdateView
from .models import Proforma, Producto, Detalle, Cliente, Supplier, Brand
from .forms import ProductoForm, ClienteForm, ProformaAddClientForm, SupplierForm, BrandForm
#reporte pdf
#from django.http import HttpResponse
#from django.template.loader import get_template
#from weasyprint import HTML
from nlt import numlet as nl

from faker import Faker

# Create your views here.

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

# Nuevo producto
def product_detail(request, id):
    producto = Producto.objects.get(id=id)
    title = 'Detalle de producto'
    context = {'producto': producto, 'title': title}
    return render(request, 'core/product/product_detail.html', context)

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

# Listar productos
class ProductListView(ListView):
    model = Producto
    template_name = 'core/product/productos_list.html'  # Nombre de la plantilla
    context_object_name = 'productos'
    context_title = 'Listado de productos'
    paginate_by = 10  # Número de productos por página

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

# Listar proformas
class ProformaListView(ListView):
    model = Proforma
    template_name = 'core/proformas_list.html'  # Nombre de la plantilla
    context_object_name = 'proformas'
    context_title = 'Listado de proformas'
    paginate_by = 10  # Número de proformas por página

    def get_queryset(self):
            query = self.request.GET.get('q')
            object_list = Proforma.objects.all().order_by('-fecha')
            if query:
                object_list = self.model.objects.filter(cliente__name__icontains = query) | object_list.filter(id__icontains=query)
            return object_list

# Crear proforma
def proforma_new(request):
    query = request.GET.get('q')
    
    # Verificar si la última proforma creada no tiene productos en su detalle
    last_proforma = Proforma.objects.last()
    if last_proforma and Detalle.productos_list(last_proforma).count() < 1:
        proforma = last_proforma
    else:
        proforma = Proforma.objects.create()
        
    detalles = Detalle.productos_list(proforma)
    productos_list = Producto.objects.all()
    literal = numero_a_literal(proforma.total)    
    
    if query:
        productos_list = productos_list.filter(nombre__icontains=query)
    
    paginator = Paginator(productos_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'proforma': proforma,
        'productos_list': page_obj,
        'detalles': detalles,
        'page_obj': page_obj,
        'literal': literal
    }

    return render(request, 'core/proforma_new.html', context)
    

def proforma_add_client(request, id):
    proforma = Proforma.objects.get(id=id)
    if request.method == 'POST':
        form = ProformaAddClientForm(request.POST, instance=proforma)
        if form.is_valid():
            form.save()
            return redirect('proforma_edit', id)
    else:
        clients_list = Cliente.objects.all()
        form = ProformaAddClientForm(instance=proforma)
        if query := request.GET.get('q'):
            clients_list = clients_list.filter(name__icontains=query)
            paginator = Paginator(clients_list, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            context = {
                'form': form,
                'clients_list': page_obj,
                'proforma': proforma, 
                'page_obj': page_obj
            }
        else:
            paginator = Paginator(clients_list, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            context = {
                'form': form,
                'clients_list': page_obj,
                'proforma': proforma, 
                'page_obj': page_obj
            }
            
    return render(request, 'core/proforma_add_client.html', context)

# Editar proforma 
def proforma_edit(request, id):
    proforma = Proforma.objects.get(id=id)
    detalles = Detalle.productos_list(proforma)
    productos_list = Producto.objects.all()
    literal = numero_a_literal(proforma.total)
    
    if query := request.GET.get('q'):
        productos_list = productos_list.filter(nombre__icontains=query)
        paginator = Paginator(productos_list, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {'proforma': proforma, 'productos_list': page_obj, 'detalles': detalles, 'page_obj': page_obj, 'literal': literal}
    else:
        paginator = Paginator(productos_list, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context = {'proforma': proforma, 'productos_list': page_obj, 'detalles': detalles, 'page_obj': page_obj, 'literal': literal}
        
    return render(request, 'core/proforma_new.html', context)

# Agregar producto a detalle
def agregar_producto_a_detalle(request):
    # VALIR DATOS SI ES POST O GET
    if request.method == 'POST':
        proforma_id = request.POST.get('proforma_id')
        producto_id = request.POST.get('producto_id')
        cantidad = request.POST.get('cantidad')  
        precio = request.POST.get('precio')
        if not cantidad:
            return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))
        if not precio:
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
        # REDIRECCIONAR A LA MISMA PAGINA
        return redirect(reverse_lazy('proforma_edit', args=[proforma_id]))
    else:
        return render(request, 'core/home.html')

# Eliminar detalle
def eliminar_producto_a_detalle(request, id):
    detalle = Detalle.objects.get(id=id)
    proforma = detalle.proforma
    proforma.total = float(proforma.total) - float(detalle.subtotal)
    proforma.save()
    detalle.delete()
    return redirect(reverse_lazy('proforma_edit', args=[proforma.id]))
    
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
        object_list = Cliente.objects.all()
        if query:
            object_list = object_list.filter(name__icontains=query) | object_list.filter(nit__icontains=query)
        return object_list

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

def cliente_delete(request, id):
    cliente = Cliente.objects.get(id=id)
    cliente.delete()
    return redirect('client_list')

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

# Marcas

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
    