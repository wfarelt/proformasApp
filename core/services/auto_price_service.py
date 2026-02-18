from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Q
from core.models import Producto
from core.services.price_evaluation_service import PriceEvaluationService
from core.services.price_approval_service import PriceApprovalService


class AutoPriceService:

    @staticmethod
    def generate_missing_prices(margin=Decimal('0.35'), auto_approve=True, user=None):
        """Genera precios faltantes para productos sin precio.
        
        Args:
            margin: Margen de ganancia (ej: 0.35 = 35%)
            auto_approve: Si True, aprueba automáticamente los precios
            user: Usuario que genera los precios (para auditoría)
            
        Returns:
            Dict con estadísticas del proceso
        """
        margin = Decimal(str(margin))

        
     
        products_list = list(Producto.objects.filter(
            stock__gt=0,
            cost__gt=0
        ).filter(
            Q(precio__isnull=True) | Q(precio=0)
        ))
        
        total = len(products_list)
        updated = 0
        failed = 0
        errors = []

        for product in products_list:
            try:
                new_price = (product.cost * (Decimal('1.00') + margin)).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP
                )

                history = PriceEvaluationService.propose_new_price(
                    product=product,
                    old_price=product.precio if product.precio else Decimal('0'),
                    new_price=new_price,
                    cost_reference=product.cost,
                    user=user,
                    reason=f"Generación automática margen {margin * 100}%",
                    change_type='ADJUSTMENT',
                    auto_approve_on_increase=auto_approve
                )

                updated += 1
            except Exception as e:
                failed += 1
                errors.append({
                    'product_id': product.id,
                    'error': str(e)
                })

        return {
            "status": "success",
            "total": total,
            "updated": updated,
            "failed": failed,
            "margin": float(margin),
            "auto_approve": auto_approve,
            "errors": errors if errors else None
        }
