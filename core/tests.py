from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch
from io import BytesIO

from openpyxl import Workbook, load_workbook
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Company, Detalle, Producto, Proforma, User
from core.services.product_catalog_import_service import ProductCatalogImportService


class ProformaRecommendationTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(
			name='Empresa Test',
			tax_id='123456',
			email='empresa@test.com',
			enable_product_recommendations=True,
		)
		self.user = User.objects.create_user(
			username='tester',
			email='tester@test.com',
			name='Tester',
			password='secret123',
			company=self.company,
		)
		self.client.force_login(self.user)

	def _create_producto(self, codigo, precio=10):
		return Producto.objects.create(nombre=codigo, precio=precio, latest_price=precio, stock=10)

	def _create_proforma(self, estado='PENDIENTE', cliente=None):
		return Proforma.objects.create(
			usuario=self.user,
			company=self.company,
			estado=estado,
			cliente=cliente,
		)

	def _add_detalle(self, proforma, producto, cantidad=1, precio=None):
		precio = precio or producto.precio
		return Detalle.objects.create(
			proforma=proforma,
			producto=producto,
			cantidad=cantidad,
			precio_venta=precio,
			subtotal=precio * cantidad,
		)

	def test_recommended_products_use_only_executed_proformas_and_exclude_current_products(self):
		producto_a = self._create_producto('A-001')
		producto_b = self._create_producto('B-001')
		producto_c = self._create_producto('C-001')
		producto_d = self._create_producto('D-001')

		current_proforma = self._create_proforma()
		self._add_detalle(current_proforma, producto_c, cantidad=1)

		executed_proforma_1 = self._create_proforma(estado='EJECUTADO')
		self._add_detalle(executed_proforma_1, producto_c, cantidad=1)
		self._add_detalle(executed_proforma_1, producto_a, cantidad=2)
		self._add_detalle(executed_proforma_1, producto_b, cantidad=1)

		executed_proforma_2 = self._create_proforma(estado='EJECUTADO')
		self._add_detalle(executed_proforma_2, producto_c, cantidad=1)
		self._add_detalle(executed_proforma_2, producto_a, cantidad=1)

		executed_proforma_3 = self._create_proforma(estado='EJECUTADO')
		self._add_detalle(executed_proforma_3, producto_b, cantidad=1)

		pending_proforma = self._create_proforma(estado='PENDIENTE')
		self._add_detalle(pending_proforma, producto_c, cantidad=1)
		self._add_detalle(pending_proforma, producto_d, cantidad=5)

		response = self.client.get(reverse('proforma_edit', args=[current_proforma.id]))

		recommended_products = response.context['recommended_products']
		recommended_ids = [producto.id for producto in recommended_products]

		self.assertEqual(recommended_ids, [producto_a.id, producto_b.id])
		self.assertNotIn(producto_c.id, recommended_ids)
		self.assertNotIn(producto_d.id, recommended_ids)
		self.assertContains(response, 'Productos recomendados')

	def test_recommended_products_can_be_disabled_per_company(self):
		self.company.enable_product_recommendations = False
		self.company.save(update_fields=['enable_product_recommendations'])

		producto = self._create_producto('A-001')
		executed_proforma = self._create_proforma(estado='EJECUTADO')
		self._add_detalle(executed_proforma, producto, cantidad=1)
		current_proforma = self._create_proforma()

		response = self.client.get(reverse('proforma_edit', args=[current_proforma.id]))

		self.assertFalse(response.context['enable_product_recommendations'])
		self.assertEqual(response.context['recommended_products'], [])
		self.assertNotContains(response, 'Productos recomendados')


class RoleAccessTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(
			name='Empresa Roles',
			tax_id='ROLE-123',
			email='roles@test.com',
		)

	def _create_user(self, username, role):
		return User.objects.create_user(
			username=username,
			email=f'{username}@test.com',
			name=username.title(),
			password='secret123',
			company=self.company,
			role=role,
		)

	def test_superadmin_sees_configuration_dashboard_only(self):
		user = self._create_user('superconfig', User.Roles.SUPERADMIN)
		self.client.force_login(user)

		response = self.client.get(reverse('home'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Panel de configuración')
		self.assertNotContains(response, 'Productos')

	def test_superadmin_is_redirected_from_operational_module(self):
		user = self._create_user('superblocked', User.Roles.SUPERADMIN)
		self.client.force_login(user)

		response = self.client.get(reverse('product_list'))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('home'))

	def test_ventas_cannot_access_inventory_module(self):
		user = self._create_user('ventasuser', User.Roles.VENTAS)
		self.client.force_login(user)

		response = self.client.get(reverse('movement_list'))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('home'))

	def test_almacen_can_access_inventory_module(self):
		user = self._create_user('almacenuser', User.Roles.ALMACEN)
		self.client.force_login(user)

		response = self.client.get(reverse('movement_list'))

		self.assertEqual(response.status_code, 200)

	def test_admin_can_open_user_management(self):
		user = self._create_user('adminpanel', User.Roles.ADMIN)
		self.client.force_login(user)

		response = self.client.get(reverse('user_list'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Usuarios')

	def test_admin_can_create_user_and_assign_role(self):
		user = self._create_user('admincreator', User.Roles.ADMIN)
		self.client.force_login(user)

		response = self.client.post(reverse('user_create'), {
			'username': 'nuevoalmacen',
			'email': 'nuevoalmacen@test.com',
			'name': 'Nuevo Almacen',
			'company': self.company.id,
			'role': User.Roles.ALMACEN,
			'password1': 'Secret12345*',
			'password2': 'Secret12345*',
		})

		self.assertEqual(response.status_code, 302)
		created_user = User.objects.get(username='nuevoalmacen')
		self.assertEqual(created_user.role, User.Roles.ALMACEN)

	def test_ventas_cannot_open_user_management(self):
		user = self._create_user('ventasblocked', User.Roles.VENTAS)
		self.client.force_login(user)

		response = self.client.get(reverse('user_list'))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('home'))

	def test_admin_can_open_company_data_panel(self):
		user = self._create_user('admincompany', User.Roles.ADMIN)
		self.client.force_login(user)

		response = self.client.get(reverse('company_edit'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Datos de la empresa')

	def test_admin_can_update_company_general_data(self):
		user = self._create_user('adminupdatecompany', User.Roles.ADMIN)
		self.client.force_login(user)

		response = self.client.post(reverse('company_edit'), {
			'name': 'Empresa Actualizada',
			'tax_id': 'ROLE-123',
			'phone': '7777777',
			'email': 'empresa-actualizada@test.com',
			'address': 'Av. Principal 123',
			'city': 'La Paz',
			'website': 'https://empresa.test',
			'industry': 'Tecnología',
			'established_date': '2024-01-15',
		})

		self.assertEqual(response.status_code, 302)
		self.company.refresh_from_db()
		self.assertEqual(self.company.name, 'Empresa Actualizada')
		self.assertEqual(self.company.city, 'La Paz')

	def test_ventas_cannot_open_company_data_panel(self):
		user = self._create_user('ventascompanyblocked', User.Roles.VENTAS)
		self.client.force_login(user)

		response = self.client.get(reverse('company_edit'))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('home'))


class CloudCatalogSuperadminTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(
			name='Empresa Catalogos',
			tax_id='CAT-123',
			email='catalogos@test.com',
		)
		self.superadmin = User.objects.create_user(
			username='supercatalog',
			email='supercatalog@test.com',
			name='Super Catalog',
			password='secret123',
			company=self.company,
			role=User.Roles.SUPERADMIN,
		)

	@patch('core.views.ProductCatalogImportService.publish_cloud_catalog_index_changes')
	@patch('core.views.ProductCatalogImportService.rename_cloud_catalog')
	def test_superadmin_can_rename_cloud_catalog(self, rename_mock, publish_mock):
		rename_mock.return_value = {
			'name': 'Catalogo Renombrado',
			'slug': 'electronica',
		}

		self.client.force_login(self.superadmin)
		response = self.client.post(reverse('superadmin_cloud_catalog_rename'), {
			'slug': 'electronica',
			'name': 'Catalogo Renombrado',
			'publish_now': 'on',
		})

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('superadmin_cloud_catalog_upload'))
		rename_mock.assert_called_once_with(slug='electronica', new_name='Catalogo Renombrado')
		publish_mock.assert_called_once_with(commit_message='Rename catalog electronica')

	@patch('core.views.ProductCatalogImportService.publish_cloud_catalog_delete')
	@patch('core.views.ProductCatalogImportService.delete_cloud_catalog')
	def test_superadmin_can_delete_cloud_catalog(self, delete_mock, publish_mock):
		delete_mock.return_value = {
			'catalog': {
				'name': 'Catalogo Legacy',
				'slug': 'legacy',
			},
			'deleted_file_path': None,
		}

		self.client.force_login(self.superadmin)
		response = self.client.post(reverse('superadmin_cloud_catalog_delete'), {
			'slug': 'legacy',
			'publish_now': 'on',
		})

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('superadmin_cloud_catalog_upload'))
		delete_mock.assert_called_once_with(slug='legacy')
		publish_mock.assert_called_once_with(
			deleted_file_path=None,
			commit_message='Delete catalog legacy',
		)


class ProductCatalogImportTemplateTests(TestCase):
	def test_generated_template_contains_expected_headers(self):
		template_bytes = ProductCatalogImportService.build_template_file()
		workbook = load_workbook(BytesIO(template_bytes))
		sheet = workbook.active

		headers = [cell.value for cell in sheet[1]]
		self.assertEqual(headers, ['Código', 'Referencia cruzada', 'Descripción'])

	def test_import_maps_referencia_cruzada_and_descripcion(self):
		workbook = Workbook()
		sheet = workbook.active
		sheet.append(['Código', 'Referencia cruzada', 'Descripción'])
		sheet.append(['ABC-001', 'REF-001', 'Producto A'])

		buffer = BytesIO()
		workbook.save(buffer)
		buffer.seek(0)

		uploaded_file = SimpleUploadedFile(
			name='catalogo.xlsx',
			content=buffer.getvalue(),
			content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
		)

		result = ProductCatalogImportService.import_from_excel(uploaded_file)
		self.assertEqual(result['created'], 1)

		producto = Producto.objects.get(nombre='ABC-001')
		self.assertEqual(producto.referencia_cruzada, 'REF-001')
		self.assertEqual(producto.descripcion, 'Producto A')
