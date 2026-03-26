
# -*- coding: utf-8 -*-

# from models.farmers import Assets
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError
from datetime import datetime, date
from odoo.tools import SQL
import logging
_logger = logging.getLogger(__name__)


class CrossoveredBudgetAdditions(models.Model):
    _inherit = "budget.analytic"

    project_id = fields.Many2one("project.project", string="Project")
    partner_id = fields.Many2one("res.partner", string="Customer")
    product_specification = fields.Many2one(
        "product.specification", string="Product Specification")

    def write(self, vals):
        res = super().write(vals)
        if self.project_id and not self.project_id.budget_id:
            self.project_id.write({
                'budget_id': self.id,
            })
        return res


class BudgetLinesAdditions(models.Model):
    _inherit = "budget.line"
    _rec_name = "budget_name"

    budget_name = fields.Char("Name", compute="_compute_line_name",
                              store=True)

    quantity = fields.Float("Quantity")
    practical_quantity = fields.Float(
        "Actual Quantity", compute="compute_practical_quantity")
    remaining_quantity = fields.Float(
        "Remaining Quantity", compute="compute_remaining_qty")
    unit_price = fields.Monetary("Unit Price", currency_field="currency_id")
    product_id = fields.Many2one('product.product', string="Product")
    description = fields.Text(string="Description")
    project_id = fields.Many2one('project.project', string="Project")
    percentage_achieved = fields.Float(
        "Achievement", compute="_compute_percentage_achieved")
    product_specification = fields.Many2one(
        "product.specification", string="Product Specification")
    
    achieved_amount = fields.Monetary(
        compute='_compute_achieved_amount',
        string='Achieved',
        help="Amount Billed/Invoiced.")
    achieved_percentage = fields.Float(
        compute='_compute_percentage_achieved',
        string='Achieved (%)')
    committed_amount = fields.Monetary(
        compute='_compute_commited_amount',
        string='Committed',
        help="Already Billed amount + Confirmed purchase orders.")
    committed_percentage = fields.Float(
        compute='_compute_commited_amount',
        string='Committed (%)')
    budget_amount = fields.Monetary(string='Budgeted', store=True, compute='_compute_budget_amount')
    
    def _get_analytic_account_field(self):
        """
        Returns the name of the first Many2one field on budget.line that references 
        account.analytic.account and has a value set (i.e., a non-empty analytic account ID).
        Falls back to 'account_id' if no field has a value.
        """
        self.ensure_one()
        model = self.env['ir.model'].sudo().search([('model', '=', 'budget.line')], limit=1)
        if not model:
            return 'account_id'  # Fallback to default

        # Get all Many2one fields related to account.analytic.account
        analytic_fields = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', model.id),
            ('ttype', '=', 'many2one'),
            ('relation', '=', 'account.analytic.account'),
        ])

        if not analytic_fields:
            return 'account_id'  # Fallback to default

        # Check each field for a non-empty value
        for field in analytic_fields:
            if self[field.name] and self[field.name].id:
                return field.name

        # Fallback to default if no field has a value
        return 'account_id'

    @api.depends('unit_price', 'quantity')
    def _compute_budget_amount(self):
        for line in self:
            if line.unit_price > 0 and line.quantity > 0:
                line.budget_amount = line.unit_price * line.quantity
            else:
                line.budget_amount = 0.0
    
    # @api.onchange('product_id','quantity','budget_amount')
    # def set_budget_line_unit_value(self):
    #     for item in self:
    #         if item.product_id and item.quantity > 0 and item.budget_amount > 0:
    #             item.unit_price = item.budget_amount / item.quantity

    def _compute_percentage_achieved(self):
        for rec in self:
            if rec.budget_amount > 0 and rec.achieved_amount > 0:
                rec.percentage_achieved = round(
                    ((rec.achieved_amount/rec.budget_amount)), 2)
            else:
                rec.percentage_achieved = 0.0

    def compute_practical_quantity(self):
        for line in self:
            if line.product_id and line.product_id.type == 'product' and line.project_id.location_id or line.budget_analytic_id.project_id.location_id:
                result = line.query_stock_moves_sql(start_date=line.date_from, end_date=line.date_to, product_id=line.product_id.id,
                                                    location_id=line.project_id.location_id.id or line.budget_analytic_id.project_id.location_id.id)
                print(result)
                line.practical_quantity = result[0] if result else 0
            else:
                line.practical_quantity = 0

    def compute_remaining_qty(self):
        for line in self:
            line.remaining_quantity = line.quantity - line.practical_quantity

    def query_stock_moves_sql(self, start_date, end_date, product_id, location_id):
        self.ensure_one()  # Ensure the method is called for a single project

        # Base SQL query
        query = """
            SELECT SUM(sml.quantity_product_uom) AS total_quantity
            FROM stock_move_line as sml
            join stock_location as sld on sml.location_dest_id  = sld.id
            WHERE sml.location_dest_id = %s OR sml.location_id = %s
            AND sml.date >= %s
            AND sml.date <= %s
            AND sml.state = 'done'
            AND sld.usage != 'internal'
        """

        params = [location_id,location_id, start_date, end_date]

        # Add product filter if product_ids are provided
        if product_id:
            query += " AND product_id = %s"
            # Convert list to tuple for SQL IN clause
            params.append(product_id)

        # Group by product
        query += " GROUP BY product_id"

        # Execute the query with parameters
        self.env.cr.execute(query, params)
        result = self.env.cr.fetchone()

        # Returning the results as a list of tuples (product_id, total_quantity)
        return result

    remaining_amount = fields.Monetary(
        compute='_compute_remaining_amount', string='Remaining Amount')

    def _compute_remaining_amount(self):
        for line in self:
            balance = 0
            if line.budget_amount != 0.00:
                balance = line.budget_amount

                if line.achieved_amount != 0.00:
                    balance = line.budget_amount - line.achieved_amount

            line.remaining_amount = balance

    # def _compute_achieved_amount(self):
    #     for line in self:
    #         # acc_ids = line.general_budget_id.account_ids.ids
    #         date_to = line.budget_analytic_id.date_to
    #         date_from = line.budget_analytic_id.date_from
    #         journal_id = self.env.ref("account.1_inventory_valuation").id
    #         if line.account_id:
    #             analytic_line_obj = self.env['account.analytic.line']
    #             domain = [('account_id', '=', line.account_id.id),
    #                       ('date', '>=', date_from),
    #                       ('date', '<=', date_to),
    #                       ('move_line_id.journal_id','!=',journal_id)
    #                       ]
    #             if line.product_id:
    #                 domain += [('product_id', '=', line.product_id.id)]

    #                 if line.product_id.categ_id.property_stock_journal and line.product_id.categ_id.property_stock_journal.id != journal_id:
    #                     domain += [('move_line_id.journal_id','!=',line.product_id.categ_id.property_stock_journal.id)]
                        
                    
    #                 # if line.project_id:
    #                 #     domain  += [('project_id', '=', line.project_id.id)]
    #                 # if line.project_id:
    #                 #     domain += [('project_id', '=', line.project_id.id)]

    #                 # where_query = analytic_line_obj._where_calc(domain)
    #                 # analytic_line_obj._apply_ir_rules(where_query, 'read')
    #                 # from_clause, where_clause, where_clause_params = where_query.get_sql()
    #                 # select = "SELECT SUM(amount) from " + \
    #                 #     from_clause + " where " + where_clause
    #                 amount = 0
    #                 analytics = analytic_line_obj.read_group(domain,['amount:sum'],['account_id'])
    #                 for anl in analytics:
    #                     amount += anl['amount']
    #                 line.achieved_amount = abs(amount)
    #             else:
    #                 line.achieved_amount = 0
                                    

    #         else:
    #             # aml_obj = self.env['account.move.line']
    #             # domain = [
                    
    #             #     ('date', '>=', date_from),
    #             #     ('date', '<=', date_to)
    #             # ]

    #             # if line.product_id:
    #             #     domain += [('product_id', '=', line.product_id.id)]
    #             # # Add line
    #             # # if line.project:
    #             # #     domain += [('project_id', '=', line.project_id.id)]

    #             # # where_query = aml_obj._where_calc(domain)
    #             # # aml_obj._apply_ir_rules(where_query, 'read')
    #             # # from_clause, where_clause, where_clause_params = where_query.get_sql()
    #             # # select = "SELECT sum(credit)-sum(debit) from " + \
    #             # #     from_clause + " where " + where_clause
                
    #             # amount = 0
    #             # analytics = aml_obj.read_group(domain,['debit:sum','credit:sum'],['account_id'])
    #             # for anl in analytics:
    #             #     amount+= anl['debit'] - anl['credit']
    #             line.achieved_amount = 0

            
    #             # line.achieved_amount = self.env.cr.fetchone()[0] or 0.0
    
    def _compute_achieved_amount(self):
        for line in self:
            # Get the analytic account field dynamically
            analytic_field = line._get_analytic_account_field()
            analytic_account_id = line[analytic_field].id if line[analytic_field] else False

            if analytic_account_id:
                date_to = line.budget_analytic_id.date_to
                date_from = line.budget_analytic_id.date_from
                journal_id = self.env.ref("account.1_inventory_valuation").id

                # Build domain for analytic lines
                domain = [
                    (analytic_field, '=', analytic_account_id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('move_line_id.journal_id', '!=', journal_id),
                ]
                if line.product_id:
                    domain += [('product_id', '=', line.product_id.id)]
                    if line.product_id.categ_id.property_stock_journal and line.product_id.categ_id.property_stock_journal.id != journal_id:
                        domain += [('move_line_id.journal_id', '!=', line.product_id.categ_id.property_stock_journal.id)]

                # Compute achieved amount
                amount = 0
                analytics = self.env['account.analytic.line'].read_group(
                    domain,
                    ['amount:sum'],
                    ['account_id']
                )
                for anl in analytics:
                    amount += anl['amount']
                line.achieved_amount = abs(amount)
            else:
                line.achieved_amount = 0.0

    def action_open_budget_entries(self):
        for rec in self:
            analytic_field = rec._get_analytic_account_field()
            analytic_account_id = rec[analytic_field].id if rec[analytic_field] else False
            if analytic_account_id:
                # if there is an analytic account, then the analytic items are loaded
                # action = self.env['ir.actions.act_window']._for_xml_id(
                #     'analytic.account_analytic_line_action_entries')
                
                domain = [(analytic_field, '=', analytic_account_id),
                                    ('date', '>=', rec.budget_analytic_id.date_from),
                                    ('date', '<=', rec.budget_analytic_id.date_to),
                                    ]
                # if self.general_budget_id:
                #     action['domain'] += [('general_account_id',
                #                           'in', self.general_budget_id.account_ids.ids)]
                if rec.product_id:
                    domain += [('product_id', '=', rec.product_id.id)]
                # if self.project_id:
                #     action['domain'] += [('project_id', '=', self.project_id.id)]
                return {
                    'name':"Budget Entries",
                    'domain':domain,
                    'res_model':"account.analytic.line",
                    'view_mode':'list,form',
                    'type':'ir.actions.act_window',
                    'target':'current',
                    'context':{'create':False, 'delete':False,'edit':False}
                }

            else:
                # otherwise the journal entries booked on the accounts of the budgetary postition are opened
                # action = self.env['ir.actions.act_window']._for_xml_id(
                #     'account.action_account_moves_all_a')
                domain = [
                    ('parent_state','=','posted'),
                    ('date', '>=', rec.date_from),
                    ('date', '<=', rec.date_to),
                ]
                if rec.product_id:
                    domain = [('product_id', '=', rec.product_id.id)]
                
                return {
                    'name':"Budget Entries",
                    'domain':domain,
                    'res_model':"account.move.line",
                    'view_mode':'list,form',
                    'type':'ir.actions.act_window',
                    'target':'current',
                    'context':{'create':False, 'delete':False,'edit':False}
                }

    @api.depends("budget_analytic_id", "account_id", "product_id", "description")
    def _compute_line_name(self):
        # just in case someone opens the budget line in form view
        for record in self:
            if not record.project_id and not record.product_id:
                computed_name = record.budget_analytic_id.name
                # if record.general_budget_id:
                #     computed_name += ' - ' + record.general_budget_id.name
                if record.account_id:
                    computed_name += ' - ' + record.account_id.name
                record.budget_name = computed_name
            else:
                compute_name = "Budget for "
                if record.project_id:
                    compute_name += " " + record.project_id.name
                if record.product_id:
                    compute_name += " - " + record.product_id.name
                if record.description:
                    compute_name += " " + record.description
                record.budget_name = compute_name

    @api.model_create_multi
    def create(self, vals):
        results = super(BudgetLinesAdditions, self).create(vals)
        for res in results:
            res._compute_line_name()
        return results
    
    # def write(self, values):
        # res = super(BudgetLinesAdditions, self).write(values)
        # self._compute_line_name()
        # return res
        
    # def _compute_commited_amount(self):
    #     for line in self:
    #         journal_id = self.env.ref("account.1_inventory_valuation").id
    #         if line.account_id:
    #             domain = [('account_id','=',line.account_id.id),('move_line_id.journal_id','!=',journal_id)]
    #             if line.product_id:
    #                 domain.append(('product_id','=',line.product_id.id))
    #             if line.budget_analytic_id.date_from:
    #                 domain.append(('date','>=',line.budget_analytic_id.date_from))
    #             if line.budget_analytic_id.date_from:
    #                 domain.append(('date','<=',line.budget_analytic_id.date_to))
    #             analytic_lines = self.env['account.analytic.line'].read_group(
    #                 domain,
    #                 ['product_id', 'amount:sum',],
    #                 ['product_id']   
    #             )
    #             domain2 = [('order_id.state','in',['purchase','done']),('budget_line_id','=',False)]
    #             domain1 = [('order_id.state','=',['purchase','done']),('budget_line_id','=',line.id)]
    #             if line.product_id:
    #                 domain2.append(('product_id','=',line.product_id.id))
    #             if line.project_id:
    #                 domain2.append(('order_id.project_id','=',line.project_id.id))
    #             if line.budget_analytic_id.date_from:
    #                 domain2.append(('date_order','>=',line.budget_analytic_id.date_from))
    #             if line.budget_analytic_id.date_from:
    #                 domain2.append(('date_order','<=',line.budget_analytic_id.date_to))
    #             po_lines = self.env['purchase.order.line'].sudo().search(domain2)
    #             po_lines2 = self.env['purchase.order.line'].sudo().search(domain1)
                
    #             committed_amount  = 0
                
    #             uncommitted_amount = 0
                
    #             uncommitted_amount2 = 0
                
                
    #             uncommitted_amount = sum(line2.price_unit * (line2.product_qty - line2.qty_invoiced) for line2 in po_lines) or 0.0
                
                
    #             uncommited_amount2 = sum(line2.price_unit * (line2.product_qty - line2.qty_invoiced) for line2 in po_lines2) or 0.0
                
    #             for line2 in analytic_lines:
                    
    #                 committed_amount +=line2['amount']
    #             line.committed_amount = abs(committed_amount) + uncommitted_amount + uncommited_amount2
    #             line.committed_percentage = line.budget_amount and (line.committed_amount / line.budget_amount)
                    
    #         else:
    #             line.committed_amount = 0
    #             line.committed_percentage =0
    
    def _compute_commited_amount(self):  # Renamed from _compute_commited_amount
        for line in self:
            # Get the analytic account field dynamically
            analytic_field = line._get_analytic_account_field()
            analytic_account_id = line[analytic_field].id if line[analytic_field] else False

            journal_id = self.env.ref("account.1_inventory_valuation").id
            if analytic_account_id:
                # Domain for analytic lines
                domain = [
                    (analytic_field, '=', analytic_account_id),
                    ('move_line_id.journal_id', '!=', journal_id),
                ]
                if line.product_id:
                    domain.append(('product_id', '=', line.product_id.id))
                if line.budget_analytic_id.date_from:
                    domain.append(('date', '>=', line.budget_analytic_id.date_from))
                if line.budget_analytic_id.date_to:
                    domain.append(('date', '<=', line.budget_analytic_id.date_to))

                # Get committed amount from analytic lines
                analytic_lines = self.env['account.analytic.line'].read_group(
                    domain,
                    ['product_id', 'amount:sum'],
                    ['product_id']
                )

                # Domain for purchase orders (uncommitted)
                domain2 = [('order_id.state', 'in', ['purchase', 'done']), ('budget_line_id', '=', False)]
                domain1 = [('order_id.state', 'in', ['purchase', 'done']), ('budget_line_id', '=', line.id)]
                if line.product_id:
                    domain2.append(('product_id', '=', line.product_id.id))
                if line.project_id:
                    domain2.append(('order_id.project_id', '=', line.project_id.id))
                if line.budget_analytic_id.date_from:
                    domain2.append(('date_order', '>=', line.budget_analytic_id.date_from))
                if line.budget_analytic_id.date_to:
                    domain2.append(('date_order', '<=', line.budget_analytic_id.date_to))

                po_lines = self.env['purchase.order.line'].sudo().search(domain2)
                po_lines2 = self.env['purchase.order.line'].sudo().search(domain1)

                committed_amount = 0
                uncommitted_amount = sum(line2.price_unit * (line2.product_qty - line2.qty_invoiced) for line2 in po_lines) or 0.0
                uncommitted_amount2 = sum(line2.price_unit * (line2.product_qty - line2.qty_invoiced) for line2 in po_lines2) or 0.0

                for line2 in analytic_lines:
                    committed_amount += line2['amount']

                line.committed_amount = abs(committed_amount) + uncommitted_amount + uncommitted_amount2
                line.committed_percentage = line.budget_amount and (line.committed_amount / line.budget_amount)
            else:
                line.committed_amount = 0
                line.committed_percentage = 0
                
           
    def _compute_all(self):
        grouped = {
            line: (committed, achieved)
            for line, committed, achieved in self.env['budget.report']._read_group(
                domain=[('budget_line_id', 'in', self.ids)],
                groupby=['budget_line_id'],
                aggregates=['committed:sum', 'achieved:sum'],
            )
        }
        for line in self:
            committed, achieved = grouped.get(line, (0, 0))
            line.committed_amount = committed
            line.achieved_amount = achieved
            line.committed_percentage = line.budget_amount and (line.committed_amount / line.budget_amount)
            line.achieved_percentage = line.budget_amount and (line.achieved_amount / line.budget_amount)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    project_id = fields.Many2one("project.project", string="Project")
    
class BudgetReport(models.Model):
    _inherit = 'budget.report'
    
    def _get_bl_query(self, plan_fnames):
        return SQL(
            """
            SELECT CONCAT('bl', bl.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'budget.analytic' AS res_model,
                   bl.budget_analytic_id AS res_id,
                   bl.date_from AS date,
                   ba.name AS description,
                   bl.company_id AS company_id,
                   NULL AS user_id,
                   'budget' AS line_type,
                   bl.budget_amount AS budget,
                   0 AS committed,
                   0 AS achieved,
                   %(plan_fields)s
              FROM budget_line bl
              JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
            """,
            plan_fields=SQL(', ').join(self.env['budget.line']._field_to_sql('bl', fname) for fname in plan_fnames)
        )
    # def _get_pol_query(self, plan_fnames):
    #     return SQL(
    #         """
    #         SELECT (pol.id::TEXT || '-' || ROW_NUMBER() OVER (PARTITION BY pol.id ORDER BY pol.id)) AS id,
                
    #             bl.budget_analytic_id AS budget_analytic_id,
    #             bl.id AS budget_line_id,             
    #             'purchase.order' AS res_model,
    #             po.id AS res_id,
    #             po.date_order AS date,
    #             pol.name AS description,
    #             pol.company_id AS company_id,
    #             po.user_id AS user_id,
    #             'committed' AS line_type,
    #             0 AS budget,
    #             (pol.product_qty - pol.qty_invoiced) / po.currency_rate * pol.price_unit::FLOAT * (a.rate)::FLOAT AS committed,
    #             0 AS achieved,
    #             %(analytic_fields)s
    #         FROM purchase_order_line pol
    #         JOIN purchase_order po ON pol.order_id = po.id AND po.state IN ('purchase', 'done')
    #     CROSS JOIN JSONB_TO_RECORDSET(pol.analytic_json) AS a(rate FLOAT, %(field_cast)s)
    #     LEFT JOIN budget_line bl 
    #             ON (pol.budget_line_id = bl.id 
    #                 OR (pol.product_id = bl.product_id 
    #                     AND po.company_id = bl.company_id 
    #                     AND po.date_order >= bl.date_from 
    #                     AND po.date_order <= bl.date_to))
    #     LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
    #         WHERE pol.qty_invoiced < pol.product_qty
    #         AND ba.budget_type != 'revenue'
    #         """,
    #         analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('a', fname) for fname in plan_fnames),
    #         field_cast=SQL(', ').join(SQL(f'{fname} FLOAT') for fname in plan_fnames),
    #     )
        
    def _get_pol_query(self, plan_fnames):
        return SQL(
            """
            SELECT (pol.id::TEXT || '-' || ROW_NUMBER() OVER (PARTITION BY pol.id ORDER BY pol.id)) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'purchase.order' AS res_model,
                   po.id AS res_id,
                   po.date_order AS date,
                   pol.name AS description,
                   pol.company_id AS company_id,
                   po.user_id AS user_id,
                   'committed' AS line_type,
                   0 AS budget,
                   (pol.product_qty - pol.qty_invoiced) / po.currency_rate * pol.price_unit::FLOAT * (a.rate)::FLOAT AS committed,
                   0 AS achieved,
                   %(analytic_fields)s
              FROM purchase_order_line pol
              JOIN purchase_order po ON pol.order_id = po.id AND po.state in ('purchase', 'done')
        CROSS JOIN JSONB_TO_RECORDSET(pol.analytic_json) AS a(rate FLOAT, %(field_cast)s)
         LEFT JOIN budget_line bl ON (pol.budget_line_id = bl.id 
                    OR (pol.product_id = bl.product_id 
                        AND po.company_id = bl.company_id 
                        AND po.date_order >= bl.date_from 
                        AND po.date_order <= bl.date_to
                        AND %(condition)s))
         LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
             WHERE pol.qty_invoiced < pol.product_qty
               AND ba.budget_type != 'revenue'
            """,
            analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('a', fname) for fname in plan_fnames),
            field_cast=SQL(', ').join(SQL(f'{fname} FLOAT') for fname in plan_fnames),
            condition=SQL(' AND ').join(SQL(
                "(%(bl)s IS NULL OR %(a)s = %(bl)s)",
                bl=self.env['budget.line']._field_to_sql('bl', fname),
                a=self.env['budget.line']._field_to_sql('a', fname),
            ) for fname in plan_fnames)
        )
    def _get_aal_query(self, plan_fnames):
        return SQL(
            """
            SELECT CONCAT('aal', aal.id::TEXT) AS id,
                   bl.budget_analytic_id AS budget_analytic_id,
                   bl.id AS budget_line_id,
                   'account.analytic.line' AS res_model,
                   aal.id AS res_id,
                   aal.date AS date,
                   aal.name AS description,
                   aal.company_id AS company_id,
                   aal.user_id AS user_id,
                   'achieved' AS line_type,
                   0 AS budget,
                   aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS committed,
                   aal.amount * CASE WHEN ba.budget_type = 'expense' THEN -1 ELSE 1 END AS achieved,
                   %(analytic_fields)s
              FROM account_analytic_line aal
         LEFT JOIN budget_line bl ON aal.company_id = bl.company_id
                                    AND aal.product_id = bl.product_id
                                    AND aal.account_id = bl.account_id
                                 AND aal.date >= bl.date_from
                                 AND aal.date <= bl.date_to
                                 AND %(condition)s
         LEFT JOIN account_account aa ON aa.id = aal.general_account_id
         LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
             WHERE CASE
                       WHEN ba.budget_type = 'expense' THEN aal.amount < 0
                       WHEN ba.budget_type = 'revenue' THEN aal.amount > 0
                       ELSE TRUE
                   END
                   AND (SPLIT_PART(aa.account_type, '_', 1) IN ('income', 'expense') OR aa.account_type IS NULL)
            """,
            analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('aal', fname) for fname in plan_fnames),
            condition=SQL(' AND ').join(SQL(
                "(%(bl)s IS NULL OR %(aal)s = %(bl)s)",
                bl=self.env['budget.line']._field_to_sql('bl', fname),
                aal=self.env['budget.line']._field_to_sql('aal', fname),
            ) for fname in plan_fnames)
        )

class AccountAnalyticLineExtended(models.Model):
    _inherit = 'account.analytic.line'
    
    bill_name = fields.Char(string="Name", compute="_compute_bill_fields", store=True)
    bill_product = fields.Char(string="Product", compute="_compute_bill_fields", store=True)
    bill_quantity = fields.Float(string="Quantity", compute="_compute_bill_fields", store=True)
    bill_price = fields.Float(string="Price", compute="_compute_bill_fields", store=True)
    bill_amount = fields.Monetary(string="Amount", compute="_compute_bill_fields", store=True)
    
    @api.depends('move_line_id')
    def _compute_bill_fields(self):
        for line in self:
            if line.move_line_id:
                move = line.move_line_id.move_id
                line.bill_name = move.name if move else False
                line.bill_product = line.move_line_id.product_id.name if line.move_line_id.product_id else False
                line.bill_quantity = line.move_line_id.quantity if hasattr(line.move_line_id, 'quantity') else 0.0
                line.bill_price = line.move_line_id.price_unit if hasattr(line.move_line_id, 'price_unit') else 0.0
                line.bill_amount = line.move_line_id.price_total if hasattr(line.move_line_id, 'price_total') else 0.0
            else:
                line.bill_name = False
                line.bill_product = False
                line.bill_quantity = 0.0
                line.bill_price = 0.0
                line.bill_amount = 0.0
