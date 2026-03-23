from django.test import TestCase
from django.urls import reverse

from core.models import Company, Detalle, Producto, Proforma, User


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
