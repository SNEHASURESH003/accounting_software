
from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'email']

from django.contrib import admin
from accounting_app.models import Account, Client

@admin.action(description='Create Clients from Receivable Accounts')
def create_clients_from_receivable(modeladmin, request, queryset):
    count = 0
    for acc in queryset.filter(is_receivable=True):
        if not Client.objects.filter(receivable_account=acc).exists():
            Client.objects.create(
                name=acc.name,
                email=f"{acc.name.lower().replace(' ', '_')}@example.com",
                receivable_account=acc
            )
            count += 1
    modeladmin.message_user(request, f"{count} client(s) created.")

class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'is_receivable')
    actions = [create_clients_from_receivable]

admin.site.register(Account, AccountAdmin)




# admin.py
from django.contrib import admin
from .models import Employee, Payroll, ContractorPayment,Invoice

admin.site.register(Employee)
admin.site.register(Payroll)
admin.site.register(ContractorPayment)


# @admin.register(Invoice)
# class InvoiceAdmin(admin.ModelAdmin):
#     list_display = ('id', 'client', 'date', 'total_amount', 'version')
from .models import AuditLog
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_id', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['change_message', 'object_id']

# accounting_app/admin.py
from django.contrib import admin, messages
from .models import JournalEntry

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "project", "is_posted", "posted_on", "posted_by")
    actions = ["post_selected"]

    def post_selected(self, request, queryset):
        ok, fail = 0, 0
        for je in queryset:
            try:
                je.mark_posted(user=request.user)
                ok += 1
            except Exception as e:
                fail += 1
                self.message_user(request, f"JE #{je.pk} failed: {e}", level=messages.ERROR)
        self.message_user(request, f"Posted {ok}, failed {fail}.")
    post_selected.short_description = "Post selected journal entries (requires approval)"

# accounting_app/admin_period.py
from django.contrib import admin, messages
from django.utils.html import format_html
from .models import AccountingPeriod  # adjust import

@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "status", "locked_on", "locked_by", "row_actions")
    actions = ("lock_selected", "unlock_selected")  # bulk actions list (or set to None)

    @admin.display(description="Actions")  # this is just the column in list_display
    def row_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Lock</a>&nbsp;'
            '<a class="button" href="{}">Unlock</a>',
            f"./{obj.pk}/lock/",
            f"./{obj.pk}/unlock/",
        )

    # --- bulk actions shown in the actions dropdown ---
    @admin.action(description="Lock selected periods")
    def lock_selected(self, request, queryset):
        updated = 0
        for p in queryset:
            updated += int(p.lock(request.user))
        self.message_user(request, f"Locked {updated} period(s).", level=messages.SUCCESS)

    @admin.action(description="Unlock selected periods")
    def unlock_selected(self, request, queryset):
        updated = 0
        for p in queryset:
            updated += int(p.unlock(request.user))
        self.message_user(request, f"Unlocked {updated} period(s).", level=messages.SUCCESS)

    # Optional: row-level views used by row_actions buttons
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        my = [
            path("<int:pk>/lock/", self.admin_site.admin_view(self.lock_view), name="accounting_period_lock"),
            path("<int:pk>/unlock/", self.admin_site.admin_view(self.unlock_view), name="accounting_period_unlock"),
        ]
        return my + urls

    def lock_view(self, request, pk):
        from django.shortcuts import redirect
        obj = self.get_object(request, pk)
        if obj.lock(request.user):
            self.message_user(request, f"Locked {obj}.", level=messages.SUCCESS)
        else:
            self.message_user(request, f"Already locked: {obj}.", level=messages.INFO)
        return redirect("../../")

    def unlock_view(self, request, pk):
        from django.shortcuts import redirect
        obj = self.get_object(request, pk)
        if obj.unlock(request.user):
            self.message_user(request, f"Unlocked {obj}.", level=messages.SUCCESS)
        else:
            self.message_user(request, f"Already open: {obj}.", level=messages.INFO)
        return redirect("../../")


# accounting_app/admin_controls.py
from django.contrib import admin
from .models import ControlArea, ControlTask, ControlTaskInstance

@admin.register(ControlArea)
class ControlAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(ControlTask)
class ControlTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "area", "cadence", "owner", "active")
    list_filter = ("area", "cadence", "active")
    search_fields = ("title", "description")

@admin.register(ControlTaskInstance)
class ControlTaskInstanceAdmin(admin.ModelAdmin):
    list_display = ("task", "period_year", "period_month", "completed", "completed_by", "completed_on")
    list_filter = ("completed", "period_year", "period_month", "task__area")
    search_fields = ("task__title",)


# accounting_app/admin.py
from .admin_procurement import *  # noqa

# accounting_app/admin_procurement.py
from django.contrib import admin
from accounting_app.models_procurement import Vendor

# @admin.register(Vendor)
# class VendorAdmin(admin.ModelAdmin):
#     list_display = ("name", "email", "gstin", "currency", "is_active")
#     search_fields = ("name", "email", "gstin")

from django.apps import AppConfig

class AccountingAppConfig(AppConfig):
    name = 'accounting_app'

    def ready(self):
        import accounting_app.signals  # 👈 make sure to import signals

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'amount', 'date', 'latest_version')

    def latest_version(self, obj):
        from .models import VersionHistory
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(obj)
        version = VersionHistory.objects.filter(content_type=ct, object_id=obj.id).order_by('-version_number').first()
        return version.version_number if version else '-'

    latest_version.short_description = 'Version'
    
    
from django.contrib import admin
from .models import ClientContract, Retainer, BillingMilestone, Phase

admin.site.register(ClientContract)
admin.site.register(Retainer)
admin.site.register(BillingMilestone)
admin.site.register(Phase)

# admin.py

from django.contrib import admin
from .models import UserActivityLog

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'ip_address')
    search_fields = ('user__username', 'action')
    list_filter = ('action', 'timestamp')

# from django.contrib import admin
# from .models import GDPRRequest

# @admin.register(GDPRRequest)
# class GDPRRequestAdmin(admin.ModelAdmin):
#     list_display = ('user', 'request_type', 'created_at', 'processed')
from django.contrib import admin
from .models import GdprRequest

@admin.register(GdprRequest)
class GdprRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'request_type', 'status', 'timestamp']
    list_filter = ['status', 'request_type']



# branding/admin.py

from django.contrib import admin
from .models import BrandingSettings

@admin.register(BrandingSettings)
class BrandingSettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'admin_user']
    
    
    
# accounting_app/admin.py
from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_read', 'sender')
    search_fields = ('title', 'text')
    list_filter = ('is_read', 'created_at')

