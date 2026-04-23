from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import NoReverseMatch


class RoleAccessMiddleware:
    """Controla acceso por rol sin depender de grupos de Django."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return self.get_response(request)

        path = request.path
        if self._is_static_or_media(path):
            return self.get_response(request)

        if getattr(request.user, 'is_superadmin', False):
            if self._superadmin_allowed(path):
                return self.get_response(request)
            messages.error(request, 'Tu rol solo puede acceder al panel de configuración.')
            return redirect('home')

        if path.startswith('/admin/'):
            messages.error(request, 'Solo el superadmin puede acceder al panel de configuración.')
            return redirect('home')

        if getattr(request.user, 'role', None) == getattr(request.user.Roles, 'CAJA', 'CAJA'):
            if self._self_service_allowed(path):
                return self.get_response(request)
            messages.warning(request, 'El rol Caja aún está pendiente de habilitación.')
            return redirect('home')

        if getattr(request.user, 'role', None) == getattr(request.user.Roles, 'VENTAS', 'VENTAS') and path.startswith('/inv/'):
            messages.error(request, 'Tu rol no tiene acceso a este módulo.')
            return redirect('home')

        return self.get_response(request)

    def _is_static_or_media(self, path):
        return path.startswith('/static/') or path.startswith('/media/')

    def _self_service_allowed(self, path):
        allowed_paths = {
            reverse('home'),
            reverse('edit_profile'),
            reverse('password_change'),
            reverse('password_change_done'),
            reverse('logout'),
        }
        return path in allowed_paths

    def _superadmin_allowed(self, path):
        allowed_paths = set()
        for route_name in (
            'superadmin_cloud_catalog_upload',
            'superadmin_cloud_catalog_rename',
            'superadmin_cloud_catalog_delete',
        ):
            try:
                allowed_paths.add(reverse(route_name))
            except NoReverseMatch:
                continue

        # Permitir cualquier acceso a la ruta de descarga de plantilla, con o sin barra final
        plantilla_path = None
        try:
            plantilla_path = reverse('download_product_catalog_template')
        except NoReverseMatch:
            pass

        catalog_base_prefix = '/config/catalogos'

        return (
            self._self_service_allowed(path)
            or path.startswith('/admin/')
            or path in allowed_paths
            or path.startswith(f"{catalog_base_prefix}/")
            or path == catalog_base_prefix
            or (plantilla_path and (path == plantilla_path or path.startswith(plantilla_path)))
        )
