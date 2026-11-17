from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Company, Proforma, Warehouse


class ProformaReportFilterTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Empresa de prueba',
            tax_id='TEST-REPORT-1',
            email='report@example.com',
        )
        self.other_company = Company.objects.create(
            name='Otra empresa',
            tax_id='TEST-REPORT-2',
            email='other-report@example.com',
        )
        self.branch_one = Warehouse.objects.create(name='Sucursal Norte', code='REPORT-N')
        self.branch_two = Warehouse.objects.create(name='Sucursal Sur', code='REPORT-S')
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='report-admin',
            email='admin-report@example.com',
            name='Administración',
            password='test-password',
            company=self.company,
            role='ADMIN',
        )
        self.seller = user_model.objects.create_user(
            username='seller-report',
            email='seller-report@example.com',
            name='Vendedora Uno',
            password='test-password',
            company=self.company,
            role='VENTAS',
        )
        self.other_seller = user_model.objects.create_user(
            username='other-seller-report',
            email='other-seller-report@example.com',
            name='Vendedor Otra Empresa',
            password='test-password',
            company=self.other_company,
            role='VENTAS',
        )
        self.client.force_login(self.admin)

    def test_branch_and_seller_filters_are_applied_and_company_scoped(self):
        today = timezone.localdate()
        Proforma.objects.create(
            fecha=timezone.now(),
            estado='EJECUTADO',
            usuario=self.seller,
            warehouse=self.branch_two,
            company=self.company,
            total=200,
        )
        Proforma.objects.create(
            fecha=timezone.now(),
            estado='EJECUTADO',
            usuario=self.seller,
            warehouse=self.branch_one,
            company=self.company,
            total=100,
        )
        Proforma.objects.create(
            fecha=timezone.now(),
            estado='EJECUTADO',
            usuario=self.other_seller,
            warehouse=self.branch_two,
            company=self.other_company,
            total=900,
        )

        response = self.client.get(
            reverse('proforma_report'),
            {
                'fecha_inicio': (today - timedelta(days=1)).isoformat(),
                'fecha_fin': today.isoformat(),
                'warehouse_id': self.branch_two.pk,
                'seller_id': self.seller.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_general'], 200)
        self.assertEqual(len(response.context['proformas']), 1)
        self.assertEqual(response.context['proformas'][0].usuario, self.seller)
        self.assertEqual(response.context['selected_warehouse'], self.branch_two)
        self.assertEqual(response.context['selected_seller'], self.seller)
        self.assertIn('month_labels', response.context['report_data'])
        self.assertContains(response, '/static/inv/js/proforma_report.js')
        self.assertNotContains(response, 'Vendedor Otra Empresa')
