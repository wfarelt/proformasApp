import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Company, User
from django.db import transaction

# Configuración inicial: compañía, roles y usuarios

def create_initial_data():
    with transaction.atomic():
        # 1. Compañía por defecto
        company, created = Company.objects.get_or_create(
            name='Empresa Default',
            defaults={
                'tax_id': 'DEFAULT-NIT',
                'email': 'default-company@local.test',
                'address': 'Empresa creada automáticamente para administración inicial.',
                'city': 'N/A',
                'is_active': True,
            }
        )
        if created:
            print('Compañía por defecto creada.')
        else:
            print('Compañía por defecto ya existe.')

        # 2. Usuarios iniciales y roles
        initial_users = [
            {
                'username': 'superadmin',
                'email': 'superadmin@local.test',
                'name': 'Super Administrador',
                'role': User.Roles.SUPERADMIN,
                'password': 'admin123',
            },
            {
                'username': 'admin',
                'email': 'admin@local.test',
                'name': 'Administrador',
                'role': User.Roles.ADMIN,
                'password': 'admin123',
            },
            {
                'username': 'ventas',
                'email': 'ventas@local.test',
                'name': 'Usuario Ventas',
                'role': User.Roles.VENTAS,
                'password': 'ventas123',
            },
            {
                'username': 'almacen',
                'email': 'almacen@local.test',
                'name': 'Usuario Almacén',
                'role': User.Roles.ALMACEN,
                'password': 'almacen123',
            },
            {
                'username': 'caja',
                'email': 'caja@local.test',
                'name': 'Usuario Caja',
                'role': User.Roles.CAJA,
                'password': 'caja123',
            },
        ]

        for user_data in initial_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'role': user_data['role'],
                    'company': company,
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                print(f"Usuario '{user.username}' creado con rol {user.role}.")
            else:
                print(f"Usuario '{user.username}' ya existe.")

if __name__ == '__main__':
    create_initial_data()
    print('Configuración inicial completada.')
