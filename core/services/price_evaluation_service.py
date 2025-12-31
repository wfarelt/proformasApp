# core/services/price_evaluation_service.py

from core.models import Producto, ProductPriceHistory

class PriceEvaluationService:

    @staticmethod
    def propose_new_price(product: Producto, old_price: float, new_price: float, user, reason: str, cost_reference=None, change_type='MANUAL'):
        """
        Crea un ProductPriceHistory en estado PENDING.
        """
        margin_percent = None
        if cost_reference is not None and cost_reference > 0:
            margin_percent = ((new_price - cost_reference) / cost_reference) * 100

        ph = ProductPriceHistory.objects.create(
            product=product,
            old_price=old_price,
            new_price=new_price,
            cost_reference=cost_reference,
            margin_percent=margin_percent,
            change_type=change_type,
            reason=reason,
            status='PENDING',
            created_by=user
        )

        return ph
