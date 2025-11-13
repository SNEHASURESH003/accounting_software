# accounting_app/models_procurement.py
from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType

from accounting_app.models import Project, CostCenter, Currency, Account, JournalEntry, JournalItem
from accounting_app.models import ControlArea  # optional
from accounting_app.models import AccountingPeriod
from accounting_app.models import ApprovalRequest  # your generic approvals

# ---------- Reference master ----------
class Vendor(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_vendor",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_vendor", null=True, blank=True
    )

    def __str__(self): return self.name


class Product(models.Model):
    UOM_CHOICES = [("EA","Each"),("HRS","Hours"),("KG","Kilogram"),("LTR","Litre")]
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    uom = models.CharField(max_length=10, choices=UOM_CHOICES, default="EA")
    default_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_product",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_product", null=True, blank=True
    )

    def __str__(self): return f"{self.sku} - {self.name}"


# ---------- Purchase Requisition ----------
class PurchaseRequisition(models.Model):
    STATUS = [
        ("DRAFT","Draft"),
        ("SUBMITTED","Submitted"),
        ("APPROVED","Approved"),
        ("REJECTED","Rejected"),
        ("CLOSED","Closed"),
    ]
    number = models.CharField(max_length=30)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="prs_requested")
    date = models.DateField(default=now)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="DRAFT")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_purchaserequistion",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_purchaserequistion", null=True, blank=True
    )

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

 
    class Meta:
            ordering = ("-created_on",)
            constraints = [
            models.UniqueConstraint(
                fields=["owner", "number"],
                name="unique_pr_number_per_owner"
            )
        ]

    def __str__(self): return f"PR {self.number}"

    def is_approved(self):
        ct = ContentType.objects.get_for_model(PurchaseRequisition)
        return ApprovalRequest.objects.filter(target_ct=ct, target_id=str(self.pk), status="APPROVED").exists()

    def recalc_total(self):
        self.total_amount = sum((li.qty * li.unit_price for li in self.lines.all()), Decimal("0"))
        self.save(update_fields=["total_amount"])

    # def submit(self):
    #     if self.status != "DRAFT":
    #         raise ValidationError("Only draft PR can be submitted.")
    #     self.status = "SUBMITTED"
    #     self.save(update_fields=["status"])
    def send_for_approval(self):
        """
        Allow sending for approval from any state except APPROVED.
        Sets status to SUBMITTED and saves.
        """
        if self.status == "APPROVED":
            raise ValidationError("Approved PR cannot be resubmitted.")
        # If you want to forbid resubmitting CLOSED, uncomment next line:
        # if self.status == "CLOSED":
        #     raise ValidationError("Closed PR cannot be resubmitted.")
        self.status = "SUBMITTED"
        self.save(update_fields=["status"])

    def close(self):
        self.status = "CLOSED"
        self.save(update_fields=["status"])


class PurchaseRequisitionLine(models.Model):
    pr = models.ForeignKey(PurchaseRequisition, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=155, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self): return f"{self.pr.number} line"


# ---------- Purchase Order ----------
class PurchaseOrder(models.Model):
    STATUS = [
        ("DRAFT","Draft"),
        ("APPROVED","Approved"),
        ("ORDERED","Ordered"),
        ("PARTIALLY_RECEIVED","Partially Received"),
        ("RECEIVED","Received"),
        ("CLOSED","Closed"),
        ("CANCELLED","Cancelled"),
    ]
    number = models.CharField(max_length=30)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=1)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    pr = models.ForeignKey(PurchaseRequisition, on_delete=models.SET_NULL, null=True, blank=True, related_name="pos")
    status = models.CharField(max_length=24, choices=STATUS, default="DRAFT")
    order_date = models.DateField(default=now)
    expected_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_purchaseorder",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_purchaserorder", null=True, blank=True
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="pos_created")
    created_on = models.DateTimeField(auto_now_add=True)

  
    class Meta:
        ordering = ("-created_on",)
        constraints = [
        models.UniqueConstraint(
            fields=["owner", "number"],
            name="unique_po_number_per_owner"
        )
    ]


    def __str__(self): return f"PO {self.number}"

    def is_approved(self):
        ct = ContentType.objects.get_for_model(PurchaseOrder)
        return ApprovalRequest.objects.filter(target_ct=ct, target_id=str(self.pk), status="APPROVED").exists()

    @property
    def qty_status(self):
        rec = sum((li.qty_received for li in self.lines.all()), Decimal("0"))
        ord = sum((li.qty for li in self.lines.all()), Decimal("0"))
        if rec == 0: return "NOT_RECEIVED"
        if rec < ord: return "PARTIAL"
        return "FULL"

    def recalc_total(self):
        self.total_amount = sum((li.qty * li.unit_price for li in self.lines.all()), Decimal("0"))
        self.save(update_fields=["total_amount"])
    


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=155, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    qty_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    qty_invoiced = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_purchaseorderline",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_purchaserorderline", null=True, blank=True
    )
    @property
    def line_total(self):
        return (self.qty or 0) * (self.unit_price or 0)

    def __str__(self): return f"{self.po.number} line"


# ---------- Goods Receipt (GRN) ----------
class GoodsReceipt(models.Model):
    number = models.CharField(max_length=30)
    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="grns")
    date = models.DateField(default=now)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_good",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_good", null=True, blank=True
    )

    def __str__(self): return f"GRN {self.number} for {self.po.number}"


class GoodsReceiptLine(models.Model):
    grn = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="lines")
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, related_name="grn_lines")
    qty_received = models.DecimalField(max_digits=12, decimal_places=2)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_goodbill",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_goodbill", null=True, blank=True
    )

    def __str__(self): return f"{self.grn.number} line"


# ---------- Vendor Bill (AP Invoice) ----------
class VendorBill(models.Model):
    STATUS = [
        ("DRAFT","Draft"),
        ("APPROVED","Approved"),
        ("POSTED","Posted"),
        ("PAID","Paid"),
        ("CANCELLED","Cancelled"),
    ]
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    paid_on = models.DateField(null=True, blank=True)
    irn = models.CharField(max_length=100, blank=True, null=True)
    ack_no = models.CharField(max_length=100, blank=True, null=True)
    eway_bill_no = models.CharField(max_length=100, blank=True, null=True)
    number = models.CharField(max_length=30)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT)
    po = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills")
    bill_date = models.DateField(default=now)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=1)
    status = models.CharField(max_length=12, choices=STATUS, default="DRAFT")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_vendorbill",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_vendorbill", null=True, blank=True
    )

    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"VendorBill {self.number}"

    def recalc(self):
        self.subtotal = sum((li.qty * li.unit_price for li in self.lines.all()), Decimal("0"))
        self.tax_amount = sum((li.tax_amount for li in self.lines.all()), Decimal("0"))
        self.total = self.subtotal + self.tax_amount
        self.save(update_fields=["subtotal", "tax_amount", "total"])

    def is_approved(self):
        ct = ContentType.objects.get_for_model(VendorBill)
        return ApprovalRequest.objects.filter(target_ct=ct, target_id=str(self.pk), status="APPROVED").exists()

    def full_clean_for_post(self):
        # Approval + locked period
        from accounting_app.utils import is_date_locked
        if not self.is_approved():
            raise ValidationError("Bill must be approved before posting.")
        if is_date_locked(self.bill_date):
            raise ValidationError("Bill date falls in a locked accounting period.")
        # 3-way match check (price/qty tolerances)
        if self.po:
            mismatch = three_way_match(self.po, self)
            if mismatch:
                raise ValidationError(f"3-way match failed: {mismatch}")


class VendorBillLine(models.Model):
    bill = models.ForeignKey(VendorBill, on_delete=models.CASCADE, related_name="lines")
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.SET_NULL, null=True, blank=True, related_name="bill_lines")
    description = models.CharField(max_length=155, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_vendorbillline",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_vendorbillline", null=True, blank=True
    )

    def __str__(self): return f"{self.bill.number} line"


# ---------- Services: 3-way match ----------
def three_way_match(po: PurchaseOrder, bill: VendorBill, qty_tol: Decimal = Decimal("0.01"), price_tol_pct: Decimal = Decimal("2.0")) -> str | None:
    """
    Return None if ok; else reason string.
    Checks per PO line: billed qty <= received qty (+tol) and price within tolerance.
    """
    po_map = {li.id: li for li in po.lines.all()}

    # Compute received qty per po_line
    recvd = {}
    for pol in po.lines.all():
        recvd[pol.id] = sum((gl.qty_received for gl in pol.grn_lines.all()), Decimal("0"))

    for line in bill.lines.all():
        if not line.po_line_id:
            # allow non-PO charges if account provided
            if not line.account_id:
                return "Bill line without PO line must specify account."
            continue
        pol = po_map.get(line.po_line_id)
        if not pol:
            return "Bill line references missing PO line."
        # qty check
        allowed = recvd.get(pol.id, Decimal("0")) + qty_tol
        if line.qty > allowed:
            return f"Qty billed ({line.qty}) exceeds qty received ({allowed})."
        # price tolerance (%)
        if pol.unit_price > 0:
            diff_pct = (abs(line.unit_price - pol.unit_price) / pol.unit_price) * Decimal("100")
            if diff_pct > price_tol_pct:
                return f"Unit price deviates by {diff_pct:.2f}% (> {price_tol_pct}%)."
    return None


# ---------- Posting hook (optional) ----------
def post_vendor_bill(bill: VendorBill, user=None, ap_account: Account | None = None, expense_account_fallback: Account | None = None):
    """
    Create & post a JournalEntry for the vendor bill (simple version).
    Dr expense(s), Cr accounts payable (AP).
    """
    bill.full_clean_for_post()
    if not ap_account:
        # Pick first payable account as default AP
        ap_account = Account.objects.filter(is_payable=True).first()
        if not ap_account:
            raise ValidationError("No Accounts Payable account configured (is_payable=True).")

    # Create JE
    je = JournalEntry.objects.create(
        date=bill.bill_date,
        description=f"Vendor bill {bill.number} for {bill.vendor.name}",
        project=None,
        currency=bill.currency,
        exchange_rate=bill.exchange_rate,
    )
    # Lines: expenses
    total_exp = Decimal("0")
    for li in bill.lines.all():
        acct = li.account or expense_account_fallback
        if not acct:
            raise ValidationError("Bill line requires an expense account (or provide fallback).")
        amt = (li.qty * li.unit_price) + li.tax_amount
        total_exp += amt
        JournalItem.objects.create(entry=je, account=acct, debit=amt, credit=Decimal("0"), description=li.description)

    # Credit AP
    JournalItem.objects.create(entry=je, account=ap_account, debit=Decimal("0"), credit=total_exp, description=f"AP for {bill.vendor.name}")

    # mark JE posted (reuses your JE.mark_posted flow and period lock)
    je.mark_posted(user=user)

    # update bill & po lines qty_invoiced
    with transaction.atomic():
        for bli in bill.lines.select_related("po_line"):
            if bli.po_line_id:
                pol = bli.po_line
                pol.qty_invoiced = (pol.qty_invoiced or 0) + (bli.qty or 0)
                pol.save(update_fields=["qty_invoiced"])
        bill.status = "POSTED"
        bill.save(update_fields=["status"])
    return je


from django.db import models

class VendorPayment(models.Model):
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    paid_on = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_vendorpayment",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_vendorpayment", null=True, blank=True
    )

    # Razorpay
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=155, blank=True, null=True)

    PAYMENT_MODES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('upi', 'UPI'),
        ('razorpay', 'Razorpay'),
        ('credit', 'Credit'),
    ]
    payment_mode = models.CharField(max_length=50, choices=PAYMENT_MODES, default='bank_transfer')

    def __str__(self):
        return f"{self.vendor.name} – ₹{self.amount} – {self.date.strftime('%d-%m-%Y')}"

    class Meta:
        verbose_name = "Vendor Payment"
        verbose_name_plural = "Vendor Payments"
        ordering = ['-date']

