# core/services/purchase_price_service.py

from core.models import ProductPriceHistory
from core.services.price_evaluation_service import PriceEvaluationService

def create_price_history_from_purchase(purchase, user):
    """
    Genera ProductPriceHistory PENDING a partir de un Purchase confirmado.
    """
    if purchase.status != 'confirmed':
        return  # Solo procesar compras confirmadas

    for item in purchase.details.all():  # suponiendo PurchaseItem
        product = item.product
        new_price = item.sale_price if item.sale_price else item.unit_price
        cost_reference = item.unit_price

        # Crear historial pendiente
        PriceEvaluationService.propose_new_price(
            product=product,
            old_price=getattr(product, 'precio', None),
            new_price=new_price,
            user=user,
            reason=f"Generated from Purchase #{purchase.id}",
            cost_reference=cost_reference,
            change_type='PURCHASE'
        )
