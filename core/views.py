from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView
from .models import Proforma, Producto, Detalle, Cliente
from .forms import ProductoForm, ClienteForm, ProformaAddClientForm
#reporte pdf
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from nlt import numlet as nl

# Create your views here.

def home(request):
    return render(request, 'core/home.html')

# Nuevo producto
def product_detail(request, id):
    producto = Producto.objects.get(id=id)
    title = 'Detalle de producto'
    context = {'producto': producto, 'title': title}
    return render(request, 'core/product_detail.html', context)

def producto_new(request):
    form = ProductoForm()
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('productos_list')
    title = 'Nuevo producto'
    context = {'form': form, 'title': title}
    return render(request, 'core/producto_new.html', context)  

def product_edit(request, id):
    title = 'Editar producto'
    producto = get_object_or_404(Producto, pk=id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('productos_list')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'core/producto_new.html', {'form': form, 'title': title})

# Listar productos
def productos_list(request):
    productos = Producto.objects.all()
    title = 'Listado de productos'
    context = {'productos': productos, 'title': title}
    return render(request, 'core/productos_list.html', context)

# Listar proformas
def proformas_list(request):
    proformas = Proforma.objects.all()
    context = {'proformas': proformas}
    return render(request, 'core/proformas_list.html', context)

# Crear proforma
def proforma_new(request):
    proforma = Proforma.objects.create()
    productos_list = Producto.objects.all()
    context = {'proforma': proforma, 'productos_list': productos_list}
    return render(request, 'core/proforma_new.html', context)

def proforma_add_client(request, id):
    proforma = Proforma.objects.get(id=id)
    if request.method == 'POST':
        form = ProformaAddClientForm(request.POST, instance=proforma)
        if form.is_valid():
            form.save()
            return redirect('proforma_edit', id)
    else:
        form = ProformaAddClientForm(instance=proforma)
    return render(request, 'core/proforma_add_client.html', {'form': form})

# Editar proforma
def proforma_edit(request, id):
    proforma = Proforma.objects.get(id=id)
    detalles = Detalle.productos_list(proforma)
    productos_list = Producto.objects.all()
    context = {'proforma': proforma, 'productos_list': productos_list, 'detalles': detalles}
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
    template_name = 'core/client_list.html'  # Nombre de la plantilla
    context_object_name = 'clientes'
    paginate_by = 10  # Número de clientes por página

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
    context = {'form': form}
    return render(request, 'core/cliente_form.html', context)

def cliente_edit(request, id):
    cliente = get_object_or_404(Cliente, pk=id)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('client_list')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'core/cliente_form.html', {'form': form})   

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

    # Renderizar la plantilla HTML con el contexto
    template = get_template('core/proforma_template.html')
    html = template.render(context)

    # Generar el PDF usando WeasyPrint
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="proforma.pdf"'
    HTML(string=html).write_pdf(response)
    return response

# ReportesGenerales
def reportes(request):
    return render(request, 'core/reportes.html')

