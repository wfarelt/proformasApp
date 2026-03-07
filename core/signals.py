from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver


DEFAULT_GROUPS = (
	'Administrador',
	'Ventas',
	'Almacen',
	'Contabilidad',
)

# Permisos por grupo: (app_label, model_name, (acciones...))
DEFAULT_GROUP_PERMISSIONS = {
	'Administrador': [
		('core', 'company', ('add', 'change', 'delete', 'view')),
		('core', 'user', ('add', 'change', 'delete', 'view')),
		('core', 'cliente', ('add', 'change', 'delete', 'view')),
		('core', 'brand', ('add', 'change', 'delete', 'view')),
		('core', 'producto', ('add', 'change', 'delete', 'view')),
		('core', 'proforma', ('add', 'change', 'delete', 'view')),
		('core', 'detalle', ('add', 'change', 'delete', 'view')),
		('core', 'supplier', ('add', 'change', 'delete', 'view')),
		('core', 'productkit', ('add', 'change', 'delete', 'view')),
		('core', 'productkititem', ('add', 'change', 'delete', 'view')),
		('core', 'productpricehistory', ('add', 'change', 'delete', 'view')),
		('inv', 'purchase', ('add', 'change', 'delete', 'view')),
		('inv', 'purchasedetail', ('add', 'change', 'delete', 'view')),
		('inv', 'movement', ('add', 'change', 'delete', 'view')),
		('inv', 'movementitem', ('add', 'change', 'delete', 'view')),
	],
	'Ventas': [
		('core', 'proforma', ('add', 'change', 'view')),
		('core', 'detalle', ('add', 'change', 'delete', 'view')),
		('core', 'cliente', ('add', 'change', 'view')),
		('core', 'producto', ('view',)),
		('core', 'brand', ('view',)),
		('core', 'supplier', ('view',)),
		('core', 'productkit', ('view',)),
		('core', 'productkititem', ('view',)),
		('inv', 'movement', ('view',)),
		('inv', 'purchase', ('view',)),
	],
	'Almacen': [
		('core', 'producto', ('view', 'change')),
		('core', 'brand', ('view',)),
		('core', 'supplier', ('view',)),
		('core', 'proforma', ('view',)),
		('inv', 'purchase', ('add', 'change', 'view')),
		('inv', 'purchasedetail', ('add', 'change', 'delete', 'view')),
		('inv', 'movement', ('add', 'change', 'view')),
		('inv', 'movementitem', ('add', 'change', 'delete', 'view')),
	],
	'Contabilidad': [
		('core', 'proforma', ('view',)),
		('core', 'cliente', ('view',)),
		('core', 'producto', ('view',)),
		('core', 'supplier', ('view',)),
		('core', 'productpricehistory', ('view',)),
		('inv', 'purchase', ('view',)),
		('inv', 'purchasedetail', ('view',)),
		('inv', 'movement', ('view',)),
		('inv', 'movementitem', ('view',)),
	],
}


def _build_codenames(app_label, model_name, actions):
	return [f'{action}_{model_name}' for action in actions]


def _sync_group_permissions(group, permission_model):
	desired_permissions = permission_model.objects.none()

	for app_label, model_name, actions in DEFAULT_GROUP_PERMISSIONS.get(group.name, []):
		codenames = _build_codenames(app_label, model_name, actions)
		desired_permissions = desired_permissions | permission_model.objects.filter(
			content_type__app_label=app_label,
			content_type__model=model_name,
			codename__in=codenames,
		)

	group.permissions.set(desired_permissions.distinct())


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
	"""Crea grupos base y sincroniza permisos por rol."""

	Group = apps.get_model('auth', 'Group')
	Permission = apps.get_model('auth', 'Permission')

	for group_name in DEFAULT_GROUPS:
		group, _ = Group.objects.get_or_create(name=group_name)
		_sync_group_permissions(group, Permission)
