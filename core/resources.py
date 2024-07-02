from import_export import resources
from .models import Producto

class ProductResource(resources.ModelResource):
    class Meta:
        model = Producto