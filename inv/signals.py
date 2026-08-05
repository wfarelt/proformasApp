"""
Las compras confirmadas ya no deben crear movimientos desde señales.

Se centraliza la logica en inv.services.purchase_confirmation_service
para garantizar que movimiento + stock + costo se apliquen siempre en
la misma transaccion e impedir desincronizaciones.
"""
