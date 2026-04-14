from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


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
        return self._self_service_allowed(path) or path.startswith('/admin/')
