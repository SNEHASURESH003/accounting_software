from django.test import TestCase
from django.urls import reverse

class ComplianceMockTests(TestCase):

    def test_dashboard_view(self):
        response = self.client.get(reverse('compliance_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Compliance & Tax Filing Dashboard")

    def test_gstr1_report(self):
        response = self.client.get(reverse('gstr1_report'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("cgst", response.json())

    def test_gstr3b_report(self):
        response = self.client.get(reverse('gstr3b_report'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("outward_supplies", response.json())

    def test_gstr9_report(self):
        response = self.client.get(reverse('gstr9_report'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("annual_turnover", response.json())

    def test_einvoice(self):
        response = self.client.get(reverse('einvoice_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("irn", response.json())

    def test_ewaybill(self):
        response = self.client.get(reverse('ewaybill_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("eway_bill_no", response.json())

    def test_tds_report(self):
        response = self.client.get(reverse('tds_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form_26q", response.json())
