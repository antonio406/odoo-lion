{
    'name': 'Lion Sceller CRM & WhatsApp',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'WhatsApp Integration and CRM Automation',
    'description': """
        Integrates WhatsApp via Meta Cloud API.
        - Webhook for incoming messages
        - Auto-create Leads/Partners
        - Auto-assign Salespersons
        - Automated reminders
    """,
    'depends': ['crm', 'base_automation', 'sale', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/product_trend_report_views.xml',
        'views/stock_minmax_report_views.xml',
        'views/goal_achievement_report_views.xml',
        'views/customer_purchase_history_report_views.xml',
        'views/whatsapp_sales_trend_report_views.xml',
        'data/automation_data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
