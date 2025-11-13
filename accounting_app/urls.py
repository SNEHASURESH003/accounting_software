from django.urls import path, include

from .views import CustomLoginView,user_list,create_user, balance_sheet, profit_loss, reconcile_items, trial_balance, dashboard
from .views import delete_user,mark_quote_paid,account_list, create_account,invoice_list, create_invoice, invoice_detail,project_costing_report,create_project, create_payroll, payroll_list, contractor_payment_list, employee_list
from .views import  print_project_summary,gdpr_request_view, gdpr_delete_user, gdpr_export_data,expense_list,submit_expense, my_expenses, review_expenses, approve_expense, reject_expense,mark_regular_payroll_paid,mark_contractor_payroll_paid, salary_slip, get_employees_by_type,contractor_list,contractor_salary_slip,tax_declaration_view,generate_tax_summary,update_filing_status
from .views import deals_list,edit_journal_entry,project_create_edit,get_stages,forecast_rebuild_from_invoices,ar_aging_report,invoice_print_group,invoice_print,edit_superuser,delete_superuser,superuser_list,toggle_superuser_status,register_superuser,reject_je, journalentry_approvals,contract_edit,contract_delete,quote_reject,add_budget,edit_client,delete_client,add_client,print_project,  invoice_pdf,client_list,combined_tax_and_tds_list, project_list,mark_paid, delete_flash_message,clear_flash_messages,delete_message,delete_error,delete_all_messages,delete_all_errors,forgot_password_view,reset_password_view,profile_edit,profile_view,settings_view,delete_contractor,delete_employee,employee_create_for_user,view_account,messages_inbox,global_search,branding_settings,view_user,edit_user,gdpr_admin_dashboard,activity_logs_view,compliances_dashboard,generate_gstr1, generate_gstr3b, generate_gstr9, generate_einvoice, generate_ewaybill, generate_tds_report,send_monthly_pdf_report,download_monthly_summary_pdf,monthly_summary_pdf,send_monthly_summary,export_invoices_csv,invoice_report,kpi_dashboard,invoice_details,razorpay_commission_payment_callback,razorpay_invoice_payment_callback,razorpay_quote_payment_callback,quote_create,quote_approve,quote_detail,quote_list,mark_invoice_paid,deal_detail,invoice_create_for_deal, commission_create_for_deal,deal_create,pay_commission,mark_milestone_billed,contract_detail,phase_create,milestone_create,generate_invoice_for_milestone,revenue_dashboard,contract_create,contract_list,retainer_create,asset_depreciation_detail,asset_list,asset_create,asset_detail,journal_entry_detail,request_je_approval,review_je,approve_je,post_je,approvals_for_object,approval_review,approval_approve,approval_reject,approval_request_create,controls_dashboard,controls_mark_complete,audit_log_for_object,audit_log_list,refresh_variance_view,generate_cash_flow,add_what_if_scenario,delete_budget,budget_overview,cash_flow_view, forecast_table_view,forecast_form_view, what_if_scenarios, forecast_vs_actual,change_plan,pay_invoice,payment_success,invoices_history,delete_invoices,invoices_list,delete_plan,manual_renew,subscription_success,add_plan,plan_list,subscribe,create_currency,currency_list,exchange_rate_list,add_exchange_rate,cost_center_list,add_cost_center,inter_company_list,add_inter_company,deferred_revenue_list,add_deferred_revenue,download_financial_dashboard_pdf,download_tax_summary_pdf,download_project_profitability_pdf,download_budget_vs_actual_pdf,download_cash_flow_pdf,profit_loss_pdf,balance_sheet_pdf,trial_balance_pdf,version_history_all_view,manage_invoice,delete_invoice,delete_journal_entry,manage_journal_entry,journal_entry_list,update_account,delete_account,audit_log_view,financial_dashboard,tax_summary_report,project_profitability_report,budget_vs_actual_report,cash_flow_statement,filing_record_list,update_contractor_filing,contractor_filing_record_list,tax_record_list,create_tax_record,mark_tax_filed,tax_filing_report,tds_record_list,mark_tds_filed,create_tds_from_contractor,create_tds_from_payroll
from django.urls import path
from .views import messages_inbox
from .views import MyLogoutView
from accounting_app.controls import (
   
    ControlTaskListView, ControlTaskCreateView,
    ControlTaskUpdateView, ControlTaskDeleteView,
)
from accounting_app.procurement import(
    vendor_payment_success,product_create,product_list,spend_by_account_report,vendor_create, vendor_update, vendor_delete, vendor_mark_as_paid, vendor_razorpay_pay,
    pr_list,pr_create,pr_detail,pr_submit,po_list,po_create,po_detail,po_submit_for_approval,grn_create,three_way_match_report,
bill_create,bill_detail,bill_submit_for_approval,bill_post,vendor_list,vendor_create,vendor_update,vendor_delete,grn_list,bill_list
)
# from integrations.views import trello_cards_view, crm_clients_view, payment_view
# from integrations.api_views import project_list_api
urlpatterns = [
    # urls.py
path("budgets/add/", add_budget, name="add_budget"),
path("quotes/<int:pk>/reject/", quote_reject, name="quote_reject"),
# urls.py
path("contracts/<int:pk>/edit/", contract_edit, name="contract_edit"),
path("contracts/<int:pk>/delete/", contract_delete, name="contract_delete"),
 path(
        'journalentry/<int:pk>/approvals/',
        journalentry_approvals,
        name='journalentry_approvals'
    ),
  path(
        "invoices/print-group/<int:client_id>/<str:project_id>/",
        invoice_print_group,
        name="invoice_print_group",
    ),
   path("reports/ar-aging/", ar_aging_report, name="ar_aging_report"),
    path('ajax/get_stages/<int:project_id>/', get_stages, name='get_stages'),
   
   
       path("forecasts/rebuild-from-invoices/", 
         forecast_rebuild_from_invoices, 
         name="forecast_rebuild_from_invoices"),
# accounting_app/urls.py
path('invoice/<int:pk>/delete/', delete_invoice, name='delete_invoice'),
   path("register-superuser/", register_superuser, name="register_superuser"),
   path("superusers/", superuser_list, name="superuser_list"),
    path("superusers/toggle/<int:user_id>/", toggle_superuser_status, name="toggle_superuser_status"),
      path("superusers/edit/<int:user_id>/", edit_superuser, name="edit_superuser"),
    path("superusers/delete/<int:user_id>/", delete_superuser, name="delete_superuser"),




       path('messages/delete/<int:message_id>/', delete_message, name='delete_message'),
    path('errors/delete/<int:error_id>/', delete_error, name='delete_error'),
    path('messages/delete_all/', delete_all_messages, name='delete_all_messages'),
    path('errors/delete_all/', delete_all_errors, name='delete_all_errors'),
    path('inbox/flash/delete/<int:idx>/', delete_flash_message, name='delete_flash_message'),
    path('inbox/flash/clear/', clear_flash_messages, name='clear_flash_messages'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('reset-password/<uuid:token>/', reset_password_view, name='reset_password'),
      path('settings/profile/', profile_edit, name='profile_edit'),
      path('profile/', profile_view, name='profile_view'),
    path('settings/', settings_view, name='settings_view'),
     path('currencies/', currency_list, name='currency_list'),
     path('currencies/add/', create_currency, name='create_currency'),
    path('exchange-rates/',exchange_rate_list, name='exchange_rate_list'),
    path('exchange-rates/add/',add_exchange_rate, name='add_exchange_rate'),
    path('cost-centers/', cost_center_list, name='cost_center_list'),
    path('cost-centers/add/', add_cost_center, name='add_cost_center'),
    path('inter-company/', inter_company_list, name='inter_company_list'),
    path('inter-company/add/', add_inter_company, name='add_inter_company'),
    path('deferred-revenue/', deferred_revenue_list, name='deferred_revenue_list'),
    path('deferred-revenue/add/', add_deferred_revenue, name='add_deferred_revenue'),
 
    path('', CustomLoginView.as_view(), name='login'),

path('invoice/mark-paid/<int:invoice_id>/', mark_paid, name='mark_paid'),
 path('logout/', MyLogoutView.as_view(), name='logout'),

    path('users/', user_list, name='users_list'),
    path('users/create/',create_user,name='create_user'),
        path('', CustomLoginView.as_view(), name='login'),
       path("users/<int:user_id>/employee/new/",employee_create_for_user,
         name="employee_create_for_user"),
        path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
    
     path('users/<int:user_id>/view/', view_user, name='view_user'),
    path('users/<int:user_id>/edit/', edit_user, name='edit_user'),
    path("employees/<int:pk>/delete/", delete_employee, name="delete_employee"),

     path('reports/balance-sheet/', balance_sheet, name='balance_sheet'),
    path('reports/profit-loss/', profit_loss, name='profit_loss'),
    path('ledger/reconcile/', reconcile_items, name='reconcile'),
path('journal-entry/new/', manage_journal_entry, name='create_journal_entry'),
# path('journal-entry/<int:pk>/edit/', manage_journal_entry, name='update_journal_entry'),
  path('journal-entry/<int:pk>/',manage_journal_entry, name='edit_journal_entry'), 


         path('journal-entry/', journal_entry_list, name='journal_entry_list'),
  
    path('journal-entry/<int:pk>/delete/', delete_journal_entry, name='delete_journal_entry'),
 path('journal-entry/<int:pk>/', journal_entry_detail, name='journal_entry_detail'),

    path('ledger/trial-balance/', trial_balance, name='trial_balance'),
    path('dashboard/', dashboard, name='dashboard'),
       path('accounts/',account_list, name='account_list'),
    path('accounts/create/', create_account, name='create_account'),
      path('accounts/<int:account_id>/', view_account, name='view_account'),
    path('invoices/', invoice_list, name='invoice_list'),
    path('invoices/<int:pk>/edit/', manage_invoice, name='update_invoice'),

path('invoices/<int:pk>/', invoice_detail, name='invoice_detail'),
    path('invoice/<int:pk>/pdf/', invoice_pdf, name='invoice_pdf'),
    path('invoices/create/', create_invoice, name='create_invoice'),
        path("invoices/<int:pk>/print/", invoice_print, name="invoice_print"),
    
    path('invoices/<int:pk>/', invoice_detail, name='invoice_detail'),
    #  path('invoices/generate-recurring/', generate_recurring_invoices_view, name='generate_recurring_invoices'),
    # path('projects/reports/', project_reports, name='project_reports'),
       path('reports/project-costing/', project_costing_report, name='project_costing_report'),
        path('projects/edit/<int:project_id>/', project_create_edit, name='edit_project'),
        path('projects/create/', create_project, name='create_project'),
        path("print/project-summary/<int:client_id>/<str:project_name>/", print_project_summary, name="print_project_summary"),
          path("projects/", project_list, name="project_list"),
            path('payroll/create/', create_payroll, name='create_payroll'),
    path('payroll/', payroll_list, name='payroll_list'),
    # path('contractor/create/', create_contractor_payment, name='create_contractor_payment'),
    path('contractor/', contractor_payment_list, name='contractor_payment_list'),
    path("contractors/<int:pk>/delete/", delete_contractor, name="delete_contractor"),
     path('tax-tds/records/', combined_tax_and_tds_list, name='combined_tax_and_tds_list'),
        path('clients/', client_list, name='client_list'),

    # urls.py

path('payroll/employees/', employee_list, name='employee_list'),
# path('payroll/employees/create/', create_employee, name='create_employee'),
 path('payroll/<int:pk>/mark-paid/', mark_regular_payroll_paid, name='mark_regular_payroll_paid'),
    path('contractor/mark-paid/<int:pk>', mark_contractor_payroll_paid, name='mark_contractor_payroll_paid'),

# path('salary-slip/<int:pk>/download/', download_salary_slip, name='download_salary_slip'),
path('salary-slip/<int:pk>/', salary_slip, name='salary_slip'),
   path('ajax/get-employees/', get_employees_by_type, name='get_employees_by_type'),
   path('contractors/', contractor_list, name='contractor_list'),

    path('contractor/slip/<int:pk>/', contractor_salary_slip, name='contractor_salary_slip'),

    path('tax/declare/', tax_declaration_view, name='tax_declaration'),
    path('tax/summary/<int:employee_id>/', generate_tax_summary, name='generate_tax_summary'),
    path('payroll/filing/<int:pk>/', update_filing_status, name='update_filing_status'),
    # urls.py

# urls.py
path('filings/<int:payroll_id>/', filing_record_list, name='filing_record_list'),
# urls.py
path('contractor/filing/<int:pk>/', update_contractor_filing, name='update_contractor_filing'),
path('contractor/<int:contractor_payment_id>/filings/', contractor_filing_record_list, name='contractor_filing_list'),

    path('tax/', tax_record_list, name='tax_record_list'),
    path('tax/create/', create_tax_record, name='create_tax_record'),
    path('tax/<int:pk>/file/', mark_tax_filed, name='mark_tax_filed'),
    path('tax/reports/', tax_filing_report, name='tax_filing_report'),
      path('tds/', tds_record_list, name='tds_record_list'),
    # path('tds/add/', add_tds_record, name='add_tds_record'),
    path('tds/<int:pk>/file/', mark_tds_filed, name='mark_tds_filed'),
    path('tds/from-payroll/<int:payroll_id>/', create_tds_from_payroll, name='create_tds_from_payroll'),
path('tds/from-contractor/<int:contractor_id>/', create_tds_from_contractor, name='create_tds_from_contractor'),
    path('reports/cash-flow/',cash_flow_statement, name='cash_flow'),
        path('reports/budget-vs-actual/', budget_vs_actual_report, name='budget_vs_actual'),
        path('reports/project-profitability/', project_profitability_report, name='project_profitability_report'),
    path('tax/summary/', tax_summary_report, name='tax_summary_report'),
     path('financial-dashboard/', financial_dashboard, name='financial_dashboard'),



    # path('integrations/trello/', trello_cards_view, name='trello_cards'),
    # path('integrations/crm/', crm_clients_view, name='crm_clients'),
    # path('integrations/payment/', payment_view, name='payment_view'),
    # path('integrations/api/projects/', project_list_api, name='project_list_api'),
       path('', include('integrations.urls')),
        path('crm/', include('integrations.urls')),
        # path('compliance/audit-log/', audit_log_view, name='audit_log'),
         path('audit/', audit_log_list, name='audit_log_list'),
    path('audit/<str:model_name>/<str:object_id>/', audit_log_for_object, name='audit_log_object'),
           path('accounts/<int:account_id>/edit/', update_account, name='update_account'),
    path('accounts/<int:account_id>/delete/', delete_account, name='delete_account'),
   path('history/all/', version_history_all_view, name='version_history_all'),
   path('reports/trial-balance/pdf/', trial_balance_pdf, name='trial_balance_pdf'),
path('balance-sheet/pdf/',balance_sheet_pdf, name='balance_sheet_pdf'),
path('profit-loss/pdf/', profit_loss_pdf, name='profit_loss_pdf'),
  path('cash-flow/download/', download_cash_flow_pdf, name='download_cash_flow_pdf'),
  path('reports/budget-vs-actual/download/', download_budget_vs_actual_pdf, name='download_budget_vs_actual_pdf'),
  path('reports/project-profitability/download/', download_project_profitability_pdf, name='download_project_profitability_pdf'),
  path('reports/tax-summary/download/', download_tax_summary_pdf, name='download_tax_summary_pdf'),
  path('dashboard/financial-pdf/', download_financial_dashboard_pdf, name='download_financial_dashboard_pdf'),
#   path('compliance/', compliance_dashboard, name='compliance_dashboard'),
#     path('compliance/export/', export_compliance_csv, name='export_compliance_csv'),

path('plans/',plan_list, name='plan_list'),
   path('deals/', deals_list, name='deals_list'),
# path('subscribe/<int:plan_id>/', subscribe, name='subscribe'),

    path('plans/add/', add_plan, name='add_plan'),
path('subscribe/<int:plan_id>/', subscribe, name='subscribe'),
    path('success/', subscription_success, name='subscription_success'),

 path('manual-renew/<int:sub_id>/',manual_renew, name='manual_renew'),

path('change-plan/<int:sub_id>/<int:new_plan_id>/', change_plan, name='change_plan'),

    path('invoices-list/', invoices_list, name='invoices_list'),
    
    path('invoices-history/', invoices_history, name='invoices_history'),

path('plans/delete/<int:plan_id>/', delete_plan, name='delete_plan'),
       
    
path('invoice/<int:invoice_id>/delete/', delete_invoices, name='delete_invoices'),

  path('pay-invoice/<int:invoice_id>/', pay_invoice, name='pay_invoice'),
    path('payment-success/', payment_success, name='payment_success'),


 path('budgets/', budget_overview, name='budget_overview'),
     path('add/', forecast_form_view, name='forecast_add'),
    path('forecasts/', forecast_table_view, name='forecast_table'),
    path('what-if/', what_if_scenarios, name='what_if_scenarios'),
    path('cash-flow/', cash_flow_view, name='cash_flow_view'),
    path('forecast-vs-actual/',forecast_vs_actual, name='forecast_vs_actual'),
    path('budgets/delete/<int:budget_id>/', delete_budget, name='delete_budget'),
    path('what-if/add/', add_what_if_scenario, name='add_what_if_scenario'),
    path('generate-cash-flow/', generate_cash_flow, name='generate_cash_flow'),
    path('refresh-variance/', refresh_variance_view, name='refresh_variance_view'),
    path('audit/', audit_log_list, name='audit_log_list'),
    path('audit/<str:model_name>/<str:object_id>/', audit_log_for_object, name='audit_log_object'),
path("controls/", controls_dashboard, name="controls_dashboard"),
    path("controls/<int:pk>/complete/", controls_mark_complete, name="controls_mark_complete"),



#  path("approvals/<str:app_label>/<str:model>/<str:object_id>/", approvals_for_object, name="approvals_for_object"),
# urls.py
path(
    "approvals/<str:app_label>/<str:model_name>/<str:object_id>/",
    approvals_for_object,
    name="approvals_for_object"
),

    path("approvals/request/<str:app_label>/<str:model>/<str:object_id>/",approval_request_create, name="approval_request_create"),
    path("approvals/review/<int:pk>/", approval_review, name="approval_review"),
    path("approvals/approve/<int:pk>/", approval_approve, name="approval_approve"),
    path("approvals/reject/<int:pk>/", approval_reject, name="approval_reject"),
    
      path("journal-entry/<int:pk>/request-approval/", request_je_approval, name="je_request_approval"),
    path("journal-entry/approval/<int:approval_pk>/review/", review_je, name="je_review"),
    path("journal-entry/approval/<int:approval_pk>/approve/", approve_je, name="je_approve"),
    path("journal-entry/<int:pk>/post/", post_je, name="je_post"),
    path("journal-entry/approval/<int:approval_pk>/reject/", reject_je, name="je_reject"),



      
path("controls/tasks/", ControlTaskListView.as_view(), name="task_list"),
    path("controls/tasks/new/", ControlTaskCreateView.as_view(), name="task_create"),
    path("controls/tasks/<int:pk>/edit/", ControlTaskUpdateView.as_view(), name="task_update"),
    path("controls/tasks/<int:pk>/delete/", ControlTaskDeleteView.as_view(), name="task_delete"),

    


 path("proc/pr/", pr_list, name="pr_list"),
    path("proc/pr/new/", pr_create, name="pr_create"),
    path("proc/pr/<int:pk>/", pr_detail, name="pr_detail"),
    path("proc/pr/<int:pk>/submit/", pr_submit, name="pr_submit"),

    # Purchase Orders
    path("proc/po/", po_list, name="po_list"),
    path("proc/po/new/", po_create, name="po_create"),
    path("proc/po/<int:pk>/", po_detail, name="po_detail"),
    path("proc/po/<int:pk>/submit/", po_submit_for_approval, name="po_submit"),

    # Goods Receipt
    path("proc/grn/new/", grn_create, name="grn_create"),
        path("proc/grn/", grn_list, name="grn_list"),
         path("products/new/", product_create, name="product_create"),
           path("products/", product_list, name="product_list"),

    # Vendor Bills
    path("proc/bill/new/", bill_create, name="bill_create"),
      path("proc/bill/", bill_list, name="bill_list"),
    path("proc/bill/<int:pk>/", bill_detail, name="bill_detail"),
    path("proc/bill/<int:pk>/submit/", bill_submit_for_approval, name="bill_submit"),
    path("proc/bill/<int:pk>/post/", bill_post, name="bill_post"),
 path("reports/3way/", three_way_match_report, name="three_way_match"),
 path("reports/spend-by-account/", spend_by_account_report, name="spend_by_account"),



  path("proc/vendors/", vendor_list, name="vendor_list"),
  
    path("proc/vendors/new/",vendor_create, name="vendor_create"),
    path("proc/vendors/<int:pk>/edit/", vendor_update, name="vendor_update"),
    path("proc/vendors/<int:pk>/delete/", vendor_delete, name="vendor_delete"),
  
    path('vendor/bill/<int:pk>/mark-paid/', vendor_mark_as_paid, name='vendor_mark_as_paid'),
path('vendor/bill/<int:pk>/pay/', vendor_razorpay_pay, name='vendor_razorpay_pay'),

path('vendor/<int:pk>/payment-success/', vendor_payment_success, name='vendor_payment_success'),

  

    

    
     path('assets/', asset_list, name='asset_list'),
    path('assets/new/', asset_create, name='asset_create'),
    path('assets/<int:pk>/', asset_detail, name='asset_detail'),
     path("assets/<int:pk>/depreciation/", asset_depreciation_detail, name="asset_depreciation_detail"),
 

     path('expenses/submit/', submit_expense, name='submit_expense'),
    path('expenses/my/', my_expenses, name='my_expenses'),
    path('expenses/review/', review_expenses, name='review_expenses'),
    path('expenses/approve/<int:pk>/', approve_expense, name='approve_expense'),
    path('expenses/reject/<int:pk>/', reject_expense, name='reject_expense'),
    path("expenses/", expense_list, name="expense_list"),

path('contracts/', contract_list, name='contract_list'),
path('contracts/<int:contract_id>/', contract_detail, name='contract_detail'),
 path('contracts/<int:contract_id>/milestone/add/', milestone_create, name='milestone_create'),
    path('milestone/<int:milestone_id>/mark-billed/',mark_milestone_billed, name='mark_milestone_billed'),


    path('contracts/new/', contract_create, name='contract_create'),
    path('contracts/<int:contract_id>/retainer/', retainer_create, name='retainer_create'),

    path('milestone/<int:milestone_id>/invoice/', generate_invoice_for_milestone, name='generate_invoice_for_milestone'),
    path('dashboard/revenue/', revenue_dashboard, name='revenue_dashboard'),
    path('contracts/<int:contract_id>/phase/add/', phase_create, name='phase_create'),
    
   path('deals/new/<int:contract_id>/', deal_create, name='deal_create'),
   
    path('deals/<int:deal_id>/', deal_detail, name='deal_detail'),
        path('deal/<int:deal_id>/invoice/', invoice_create_for_deal, name='invoice_create_for_deal'),
    path('deal/<int:deal_id>/commission/', commission_create_for_deal, name='commission_create_for_deal'),
    path('invoices/<int:invoice_id>/pay/', mark_invoice_paid, name='mark_invoice_paid'),
path('commission/<int:commission_id>/pay/', pay_commission, name='pay_commission'),
   path('quotes/', quote_list, name='quote_list'),
    path('quotes/create/<int:deal_id>/', quote_create, name='quote_create'),
    path('quotes/<int:quote_id>/', quote_detail, name='quote_detail'),
    path('quotes/<int:quote_id>/approve/', quote_approve, name='quote_approve'),


   
   
   
    
        path('invoice/<int:invoice_id>/pay/manual/',mark_invoice_paid, name='mark_invoice_paid'),
      path('quote/<int:quote_id>/mark-paid/', mark_quote_paid, name='mark_quote_paid'),


    
    
    
    
    path('payments/invoice/callback/', razorpay_invoice_payment_callback, name='razorpay_invoice_payment_callback'),
path('payments/commission/callback/', razorpay_commission_payment_callback, name='razorpay_commission_payment_callback'),
path('payments/quote/callback/', razorpay_quote_payment_callback, name='razorpay_quote_payment_callback'),
path('invoice/<int:pk>/', invoice_details, name='invoice_details'),




    # Reporting & BI
    path('dashboard/kpis/', kpi_dashboard, name='kpi_dashboard'),
     path('reports/invoices/',invoice_report, name='invoice_report'),
     
         path('reports/export/csv/', export_invoices_csv, name='export_invoices_csv'),
          path('reports/monthly-summary/', send_monthly_summary, name='send_monthly_summary'),
          
    path('reports/monthly/', monthly_summary_pdf, name='monthly_summary_pdf'),
     path('monthly-summary/download/', download_monthly_summary_pdf, name='download_monthly_summary_pdf'),
         path('send-monthly-report/', send_monthly_pdf_report, name='send_monthly_report'),
         
          path('compliance/', compliances_dashboard, name='compliances_dashboard'),

    # path('compliance/gstr1/', gstr1_report, name='gstr1_report'),
    # path('compliance/gstr3b/', gstr3b_report, name='gstr3b_report'),
    # path('compliance/gstr9/', gstr9_report, name='gstr9_report'),

    # path('compliance/einvoice/', einvoice_view, name='einvoice_view'),
    # path('compliance/ewaybill/', ewaybill_view, name='ewaybill_view'),

    # path('compliance/tds/', tds_reports, name='tds_reports'),
  
path('compliance/', compliances_dashboard, name='compliances_dashboard'),
    path('generate/gstr1/<int:client_id>/', generate_gstr1, name='generate_gstr1'),
    path('generate/gstr3b/<int:client_id>/', generate_gstr3b, name='generate_gstr3b'),
    path('generate/gstr9/<int:client_id>/', generate_gstr9, name='generate_gstr9'),
    path('generate/tds/<int:client_id>/',generate_tds_report, name='generate_tds'),
    path('generate/einvoice/<int:client_id>/', generate_einvoice, name='generate_einvoice'),
    path('generate/ewaybill/<int:client_id>/', generate_ewaybill, name='generate_ewaybill'),
     path('activity-logs/', activity_logs_view, name='activity_logs'),
 


    path('inbox/', messages_inbox, name='messages_inbox'),

   
    path('gdpr/request/', gdpr_request_view, name='gdpr_request'),
    path('gdpr/export/<int:user_id>/', gdpr_export_data, name='gdpr_export_data'),
    path('gdpr/delete/<int:user_id>/', gdpr_delete_user, name='gdpr_delete_user'),
    path('gdpr/admin/', gdpr_admin_dashboard, name='gdpr_admin_dashboard'),
     path('settings/branding/', branding_settings, name='branding_settings'),

  path('search/', global_search, name='global_search'),

   
  

   
   path("messages/", messages_inbox, name="messages_inbox"),
    path("print/<int:project_id>/", print_project, name="print_project"),
    path("clients/add/", add_client, name="add_client"),
        path("clients/<int:pk>/edit/", edit_client, name="client_edit"),
    path("clients/<int:pk>/delete/", delete_client, name="client_delete"),


  

         
         
         
         
         
]


    
   
   
