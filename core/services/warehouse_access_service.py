from core.models import Warehouse


class WarehouseAccessDenied(ValueError):
    pass


def accessible_warehouses(user):
    warehouses = Warehouse.objects.filter(is_active=True).order_by('name')
    if user.can_manage_all_warehouses:
        return warehouses
    if user.default_warehouse_id:
        return warehouses.filter(pk=user.default_warehouse_id)
    return warehouses.none()


def default_user_warehouse(user):
    warehouse = accessible_warehouses(user).first()
    if warehouse is None:
        raise WarehouseAccessDenied('No tienes un almacén activo asignado.')
    return warehouse


def resolve_user_warehouse(user, warehouse_id=None):
    if user.can_manage_all_warehouses:
        if warehouse_id:
            warehouse = Warehouse.objects.filter(pk=warehouse_id, is_active=True).first()
            if warehouse is None:
                raise WarehouseAccessDenied('El almacén seleccionado no está disponible.')
            return warehouse
        return default_user_warehouse(user)

    warehouse = default_user_warehouse(user)
    if warehouse_id and str(warehouse.pk) != str(warehouse_id):
        raise WarehouseAccessDenied('No puedes operar en un almacén distinto al asignado.')
    return warehouse
