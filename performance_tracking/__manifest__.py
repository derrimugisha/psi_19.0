# -*- coding: utf-8 -*-
{
    'name': "Performance Tracking",
    'summary': """
        Performance Tracking Customizations""",
    'description': """
        Performance Tracking Customizations
    """,
    'author': "Tech Things",
    'website': "https://www.techthings.it",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'sale_management', 'account','crm'],
    'data': [
        'security/ir.model.access.csv',        
        'views/performance_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,

}
