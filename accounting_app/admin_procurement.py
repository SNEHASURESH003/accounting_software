# accounting_app/admin_procurement.py
from django.contrib import admin
from accounting_app.models_procurement import (
    Vendor, Product,
    PurchaseRequisition, PurchaseRequisitionLine,
    PurchaseOrder, PurchaseOrderLine,
    GoodsReceipt, GoodsReceiptLine,
    VendorBill, VendorBillLine
)

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "gstin", "currency", "is_active")
    search_fields = ("name","email","gstin")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku","name","uom","default_price")
    search_fields = ("sku","name")

class PRLineInline(admin.TabularInline):
    model = PurchaseRequisitionLine
    extra = 0

@admin.register(PurchaseRequisition)
class PRAdmin(admin.ModelAdmin):
    list_display = ("number","requester","date","status","total_amount")
    list_filter = ("status","date")
    inlines = [PRLineInline]

class POLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0

@admin.register(PurchaseOrder)
class POAdmin(admin.ModelAdmin):
    list_display = ("number","vendor","order_date","status","total_amount","currency")
    list_filter = ("status","order_date")
    inlines = [POLineInline]

class GRNLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0

@admin.register(GoodsReceipt)
class GRNAdmin(admin.ModelAdmin):
    list_display = ("number","po","date","received_by")
    inlines = [GRNLineInline]

class BillLineInline(admin.TabularInline):
    model = VendorBillLine
    extra = 0

@admin.register(VendorBill)
class VendorBillAdmin(admin.ModelAdmin):
    list_display = ("number","vendor","bill_date","status","total","currency")
    list_filter = ("status","bill_date")
    inlines = [BillLineInline]
