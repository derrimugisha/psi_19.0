# -*- coding: utf-8 -*-
{
    'name': "PSIEngineering",

    'summary': "PSIEngineering Customizations",

    'description': """
        A module to hold customizations for the PSIEngineering
    """,

    'author': "Tech Things Ltd",
    'website': "https://www.techthings.it",

   
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','stock','account','crm','purchase','sale_project','mail','requisitions','account_budget','project_account_budget','calendar','hr_expense','fleet'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'security/security.xml',
        # 'data/sequence.xml',
        # 'data/stage_data.xml',
        # 'reports/milestone_report_template.xml',
        # 'reports/stock_picking.xml',
        # 'views/sale_project.xml',
        # 'views/requisitions.xml',
        # 'views/calendar.xml',
        # 'views/views.xml',
        # 'views/balance_in_ledger.xml', 
        # 'views/crm_custom.xml',
        # 'views/cron.xml',
        # 'data/mail_template.xml', 
        # 'views/budget.xml',
        # 'views/project.xml',
        # 'views/website_forms.xml',
        # 'views/wizard.xml',
        # 'views/estimation.xml',
        # 'views/menus.xml',
        # 'views/custom_fleet.xml',
    ],
    'assets' : {
        'web.assets_backend' : [
            # 'psi_engineering/static/src/css/style.css',
        ],
       
    },
    'license': 'LGPL-3',
    'installable': True,
   
}

