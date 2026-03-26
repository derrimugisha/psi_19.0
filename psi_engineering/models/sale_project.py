from datetime import timedelta, datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging,json

_logger = logging.getLogger(__name__)


# class CashRequest(models.Model):
#     _name = 'cash.request'
#     _inherit = ['cash.request', 'mail.activity.mixin']

#     STATUS = [
#         ('draft', 'Draft'),
#         ('submitted', 'Submitted'),
#         ('finance', 'Finance Approval'),
#         ('md_approval', 'MD Approval'),
#         ('approved', 'Approved'),
#         ('cash_out', 'Cash Out'),
#         ('done', 'Done'),
#         ('cancel', 'Cancelled'),
#         ('reject', 'Rejected'),
#     ]

#     state = fields.Selection(STATUS, default='draft',
#                              tracking=True, index=True)
#     approval_date = fields.Date(string="Approval Date", tracking=True)

#     user = fields.Many2one('res.users', string="User", tracking=True)
#     project_id = fields.Many2one('project.project', string='Project')
#     task_id = fields.Many2one('project.task', string='Task')
#     sub_task_id = fields.Many2one('project.task', string='Sub Task')
#     sale_order_id = fields.Many2one('sale.order', string='Sales Order')
#     sale_order_line_id = fields.Many2one(
#         'sale.order.line', string='Sales Order Line')
#     partner_id = fields.Many2one("res.partner", string="Customer")
#     journal_id = fields.Many2one(
#         'account.journal', string="Payment Method", domain="[('type','in',['cash','bank'])]")
#     employee_id = fields.Many2one('hr.employee', string="Request Employee",
#                                   default=lambda self: self.env.user.employee_id.id if self.env.user.employee_id else False)
#     employee_journal_id = fields.Many2one(
#         'account.journal', string="Employee Journal", help="The employee's associated journal.", )
#     internal_transfer_id = fields.Many2one(
#         'account.payment', string="Internal Transfer Payment")
#     budget_id = fields.Many2one('budget.analytic', string="Budget",
#                                 domain="[('project_id', '=', project_id)]", tracking=True)
#     budget_line_id = fields.Many2one(
#         'budget.line', string="Budget Line",)
#     payment_count = fields.Integer(
#         string="Payments", compute='_compute_payment_count')
#     move_count = fields.Integer(
#         string="Journal Entries", compute='_compute_move_count')
#     lead_id = fields.Many2one('crm.lead', string="Related Lead", readonly=True)
#     currency_id = fields.Many2one(
#         'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
#     employee_threshold = fields.Float(
#         string="Threshold", related='employee_id.unreconciled_threshold', readonly=True)
#     cash_line_ids = fields.One2many(
#         'cash.request.lines', 'cash_id', string='Order Lines')

#     remaining_budget = fields.Float(
#         string="Remaining Budget", compute='_compute_remaining_budget', store=True)

#     department_id = fields.Many2one("hr.department", string="Department ")
#     employee_manager_id = fields.Many2one(
#         "hr.employee", string="Employee Manager")
#     can_approve = fields.Boolean("Can Approve Requisition", )
#     liquidity_transfer = fields.Many2one(
#         'account.account', 
#         string="Liquidity Transfer", 
#         default=lambda self: self._get_default_transfer_account()
#     )
#     amount_requested = fields.Float("Amount Requested")
#     purchase_order_id = fields.Many2one("purchase.order", string="purchase Order")
    
#     @api.model
#     def _get_default_transfer_account(self):
#         transfer_account = self.env['account.account'].search(
#             [('is_transfer_account', '=', True)], 
#             limit=1
#         )
#         return transfer_account.id if transfer_account else False

#     @api.depends('employee_id', 'department_id', 'state', 'name')
#     def compute_can_approve2(self):

#         for rec in self:
#             rec._onchange_employee_id()
#             if self.env.user.employee_id:
#                 if rec.employee_manager_id.id == self.env.user.employee_id.id:
#                     rec.can_approve = True
#                 else:
#                     # rec.can_approve = False
#                     if rec.employee_id and not rec.employee_id.parent_id:
#                         if self.env.user.has_group("psi_engineering.group_department_manager"):
#                             rec.can_approve = True
#                         else:
#                             rec.can_approve = False
#                     else:
#                         rec.can_approve = False
#             else:
#                 rec.can_approve = False

#     @api.onchange("employee_id")
#     def _onchange_employee_id(self):
#         for rec in self:
#             if rec.employee_id:
#                 rec.department_id = rec.employee_id.department_id.id if rec.employee_id.department_id else False
#                 rec.employee_manager_id = rec.employee_id.parent_id.id if rec.employee_id.parent_id.id else False

#     @api.depends('budget_line_id')
#     def _compute_remaining_budget(self):
#         """ Compute the remaining budget for the selected budget line """
#         for line in self:
#             if line.budget_line_id:
#                 # Assume `achieved_amount` is the amount already spent and `budget_amount` is the budgeted amount
#                 line.remaining_budget = line.budget_line_id.budget_amount - \
#                     line.budget_line_id.achieved_amount
#             else:
#                 line.remaining_budget = 0.0

#     def _compute_payment_count(self):
#         for rec in self:
#             rec.payment_count = self.env['account.payment'].search_count(
#                 [('cash_request_id', '=', rec.id)])

#     def _compute_move_count(self):
#         for rec in self:
#             rec.move_count = self.env['account.move'].search_count(
#                 [('requisition_id', '=', rec.id), ('move_type', '=', 'entry')])

#     def action_view_payments(self):
#         """ Return action to view payments related to this cash request """
#         return {
#             'name': 'Payments',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.payment',
#             'view_mode': 'list,form',
#             'domain': [('cash_request_id', '=', self.id)],
#             'context': {'create': False},
#         }

#     def action_view_moves(self):
#         """ Return action to view payments related to this cash request """
#         return {
#             'name': 'Journal Entries',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [('requisition_id', '=', self.id)],
#             'context': {'create': False},
#         }

#     @api.onchange('employee_id')
#     def _onchange_employee_id(self):
#         for rec in self:
#             if rec.employee_id:
#                 rec.write({
#                     'employee_journal_id': rec.employee_id.journal_id.id if rec.employee_id.journal_id else False
#                 })

#     @api.onchange('project_id', 'line_ids', 'budget_id')
#     def _onchange_project_id(self):
#         if self.project_id:
#             # Set the budget linked to the project, if available
#             budget = self.env['budget.analytic'].search(
#                 [('project_id', '=', self.project_id.id)], limit=1)
#             self.budget_id = budget.id if budget else False
#             analytic_account = self.project_id.account_id
#             for line in self.line_ids:
#                 line.analytic_account_id = analytic_account.id
#                 line.budget_id = budget.id if budget else False

#     def _create_cash_reconciliation_activity(self):
#         cash_request_model = self.env['cash.request']
#         cash_requests = cash_request_model.search([('state', '=', 'done')])

#         for request in cash_requests:

#             existing_activity = self.env['mail.activity'].search([
#                 ('res_model', '=', 'cash.request'),
#                 ('res_id', '=', request.id),
#                 # ('summary', '=', 'Cash Reconciliation Reminder')
#             ], limit=1)

#             if not existing_activity:

#                 activity_type = self.env.ref(
#                     'mail.mail_activity_data_todo', raise_if_not_found=False)
#                 if not activity_type:
#                     activity_type = self.env['mail.activity.type'].search(
#                         [('name', '=', 'To Do')], limit=1)

#                 if activity_type:

#                     employee_user = request.employee_id.user_id

#                     deadline_date = fields.Date.today() + timedelta(days=7)

#                     activity_vals = {
#                         'res_model_id': self.env['ir.model']._get('cash.request').id,
#                         'res_id': request.id,
#                         'activity_type_id': activity_type.id,
#                         'summary': 'Cash Reconciliation Reminder',
#                         'user_id': employee_user.id,
#                         'date_deadline': deadline_date,
#                         'note': _('Please complete the reconciliation for your cash requisition before the 7-day deadline.')
#                     }

#                     # try:
#                     #     self.env['mail.activity'].create(activity_vals)

#                     # except Exception as e:
#                     #     _logger.error(f"Failed to create activity for cash request ID: {request.id}. Error: {str(e)}")
#                 else:
#                     _logger.error(
#                         "Could not find or create an appropriate activity type.")

#     def get_credit_account(self):
#         for rec in self:
#             if not rec.journal_id:
#                 raise UserError(
#                     _("Please first set the Payment Method to continue"))
#             # if not rec.payment_method_line_id:
#             #     raise UserError(_("Please first set the Payment Mode to continue"))
#             if rec.journal_id:
#                 payment_line = rec.journal_id.outbound_payment_method_line_ids[0]
#                 if payment_line.payment_account_id:
#                     account = payment_line.payment_account_id.id
#                 else:
#                     account = rec.journal_id.company_id.account_journal_payment_credit_account_id.id

#                 return account

#     def _get_default_transfer_account(self):

#         account = self.env.user.company_id.transfer_account_id.id

#         return account

#     def create_second_journal_entry(self):
#         for line in self:
#             # if line.type == "internal_transfer":
#             move_line_vals = []
#             debit_line = {
#                 'account_id': line.liquidity_transfer.id,
#                 'debit': line.amount_requested if line.purchase_order_id else line.amount,
#                 'credit': 0.0,
#                 'name': line.name,
#             }
#             move_line_vals.append((0, 0, debit_line))
#             credit_line = {

#                 'account_id': line.journal_id.default_account_id.id,
#                 'debit': 0.0,
#                 'credit': line.amount_requested if line.purchase_order_id else line.amount,
#                 'name': line.name,
#             }
#             move_line_vals.append((0, 0, credit_line))
#             # journal = self.env['account.journal'].sudo().search([('default_account_id','=',line.default_account_id.id)])
#             move_vals = {
#                 'journal_id': line.journal_id.id,
#                 'requisition_id': line.id,
#                 'line_ids': move_line_vals,
#             }
#             move = self.env['account.move'].create(move_vals)
#             move.action_post()

#     def create_transfer_journal_entry(self,):
#         for line in self:
#             # if line.type == "internal_transfer":
#             move_line_vals = []
#             credit_line = {

#                 'account_id': line.liquidity_transfer.id,
#                 'debit': 0.0,
#                 'credit': line.amount_requested if line.purchase_order_id else line.amount,
#                 'name': line.name,
#             }

#             debit_line = {
#                 'account_id': line.employee_journal_id.default_account_id.id,
#                 'credit': 0.0,
#                 'debit': line.amount_requested if line.purchase_order_id else line.amount,
#                 'name': line.name,
#             }
#             move_line_vals.append((0, 0, debit_line))
#             move_line_vals.append((0, 0, credit_line))
#             # journal = self.env['account.journal'].sudo().search([('default_account_id','=',line.default_account_id.id)])
#             move_vals = {
#                 'journal_id': line.employee_journal_id.id,
#                 'requisition_id': line.id,
#                 # 'ref': line.name,
#                 'line_ids': move_line_vals,
#             }
#             move = self.env['account.move'].create(move_vals)
#             move.action_post()

#     def cash_request2(self):
#         if not self.journal_id or not self.employee_journal_id:
#             raise UserError(
#                 "Please set both the journal and the employee's journal before creating an internal transfer.")

#         self.create_second_journal_entry()
#         self.create_transfer_journal_entry()
#         # # Check if the state is 'cash_out' before proceeding
#         # if self.state != 'cash_out':
#         #     raise UserError(
#         #         "The cash requisition must be in the 'Cash Out' state to proceed.")

#         # # Create a purchase receipt in account.move
#         # move_vals = {
#         #     'move_type': 'in_receipt',  # Type of receipt
#         #     'partner_id': self.requested_by.partner_id.id,
#         #     'date': fields.Date.today(),
#         #     'invoice_date': fields.Date.today(),
#         #     'project_id': self.project_id.id,
#         #     'requisition_id': self.id,  # Assuming project_id is added to account.move
#         #     'line_ids': [],
#         # }

#         # # Iterate over the lines in the requisition to create account.move lines
#         # for line in self.line_ids:
#         #     move_line_vals = {
#         #         'account_id': line.account_id.id,
#         #         # The account for this line
#         #         'product_id': line.product_id.id if line.product_id.id else False,
#         #         'name': line.item or 'Cash Requisition Line',  # Line description
#         #         'quantity': line.qty,
#         #         'price_unit': line.unit_price,
#         #         # Analytic account from the line
#         #         'analytic_distribution': {str(line.analytic_account_id.id): 100},
#         #         'project_id': line.project_id.id,  # Related project from the line
#         #     }
#         #     move_vals['line_ids'].append((0, 0, move_line_vals))

#         # # Create the account move (purchase receipt)
#         # move = self.env['account.move'].create(move_vals)

#         # Set the requisition to the 'done' state
#         self.write({'state': 'done'})

#     def create_internal_transfer_payment(self):
#         """Create an internal transfer payment from journal_id to employee_journal_id with analytic account and project"""

#         if not self.journal_id or not self.employee_journal_id:
#             raise UserError(
#                 "Please set both the journal and the employee's journal before creating an internal transfer.")

#         # if not self.project_id or not self.project_id.analytic_account_id and not self.lead_id:
#         #     raise UserError(
#         #         "Please ensure the project and its analytic account are set. Or Please ensure that your have attached the related lead / Opportunity")

#         payment_vals = {
#             'payment_type': 'outbound',
#             'amount': self.amount,
#             'currency_id': self.company_id.currency_id.id,
#             'journal_id': self.journal_id.id,  # Source journal
#             # 'destination_journal_id': self.employee_journal_id.id,
#             'date': fields.Date.today(),
#             'memo': f"Cash Requisition {self.name}",
#             'cash_request_id': self.id,  # Link to the cash request for tracking
#             'project_id': self.project_id.id if self.project_id else False,
#             'analytic_account_id': self.project_id.account_id.id if self.project_id and self.project_id.account_id else False,
#         }

#         payment_vals2 = payment_vals.copy()
#         payment_vals2['journal_id'] = self.employee_journal_id.id
#         payment_vals2['payment_type'] = 'inbound'

#         # Create the payment
#         payment = self.env['account.payment'].create(payment_vals)

#         payment2 = self.env['account.payment'].create(payment_vals2)

#         # Link the created internal transfer to the cash request
#         self.internal_transfer_id = payment.id
#         if self.project_id and self.project_id.account_id:
#             self._set_analytic_distribution_in_journal_entries(payment)
#             self._set_analytic_distribution_in_journal_entries(payment2)
#         # Post the internal transfer payment
#         payment.action_post()
#         payment.action_validate()
#         payment2.action_post()
#         payment2.action_validate()

#         self.state = 'done'
#         self._create_cash_reconciliation_activity()

#         return payment

#     def _set_analytic_distribution_in_journal_entries(self, payment):
#         """Set the analytic distribution on the journal entries generated by the payment"""
#         analytic_distribution = {
#             self.project_id.account_id.id: 100.0,
#         }

#         for line in payment.move_id.line_ids:
#             line.analytic_distribution = analytic_distribution
#             line.project_id = self.project_id.id

#     purchase_receipt_count = fields.Integer(
#         string="Purchase Receipts", compute='_compute_purchase_receipt_count')

#     def _compute_purchase_receipt_count(self):
#         for rec in self:
#             rec.purchase_receipt_count = self.env['account.move'].search_count([
#                 ('requisition_id', '=', rec.id),
#                 ('move_type', '=', 'in_receipt')
#             ])

#     def action_view_purchase_receipts(self):
#         """ Return an action to view purchase receipts related to this cash requisition """
#         return {
#             'name': 'Purchase Receipts',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [('requisition_id', '=', self.id), ('move_type', '=', 'in_receipt')],
#             'context': {'create': False},
#         }

#     vendor_bill_count = fields.Integer(
#         string="Vendor Bills", compute='_compute_vendor_bill_count')

#     def _compute_vendor_bill_count(self):
#         for rec in self:
#             rec.vendor_bill_count = self.env['account.move'].search_count([
#                 ('requisition_id', '=', rec.id),
#                 # 'in_invoice' is for vendor bills
#                 ('move_type', '=', 'in_invoice')
#             ])

#     def action_view_vendor_bills(self):
#         """ Return an action to view vendor bills related to this cash requisition """
#         return {
#             'name': 'Vendor Bills',
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [('requisition_id', '=', self.id), ('move_type', '=', 'in_invoice')],
#             'context': {'create': False},
#         }

#     def open_expense_type_wizard(self):
#         """ Opens the wizard to select expense type """
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Select Expense Type',
#             'res_model': 'expense.type.wizard',
#             'view_mode': 'form',
#             'view_id': self.env.ref('psi_engineering.view_expense_type_wizard_form').id,
#             'target': 'new',
#             'context': {'default_expense_type': 'purchase_receipt', 'default_cash_requisition_id': self.id}
#         }

#     @api.model
#     def write(self, vals):
#         for record in self:
#             if record.state == 'done':
#                 if 'project_id' in vals or 'budget_id' in vals:
#                     raise UserError(
#                         _("You cannot modify 'Project' and 'Budget' fields when the requisition is in the 'done' state.")
#                     )
#         return super(CashRequest, self).write(vals)

#     def btn_md_approval(self):
#         for data in self:
#             data.write({'state': 'cash_out'})
#             data.approval_date = fields.Date.today()
#             data.user = self.env.uid

#     def btn_mv_submitted1(self):
#         for rec in self:
#             total_amount = 0.0
#             common_values = {
#                 'requested_by': self.env.uid,
#                 'department_id': self.env.user.employee_id.department_id.id if self.env.user.employee_id.department_id else False,
#                 'date': fields.Date.today(),
#             }
#             if not rec.purchase_order_id:
#                 for line in rec.cash_line_ids:
                    
#                     total_amount = rec.currency_id._convert(
#                         line.total_price,
#                         self.env.user.company_id.currency_id,
#                         self.env.user.company_id,
#                         fields.Date.today()
#                     )

#                     if total_amount <= 0.00:
#                         raise models.ValidationError(
#                             'Cannot request for zero (0) amounts of money!'
#                         )
#             else:
#                 if rec.amount_requested <= 0.00:
#                         raise models.ValidationError(
#                             'Cannot request for zero (0) amounts of money!'
#                         )        

            
#             rec.write({
#                 'state': 'submitted',
#                 **common_values
#             })



#     def submit_finance(self):
#         for rec in self:
#             if rec.employee_id.parent_id.id == self.env.user.employee_id.id:
#                 rec.write({
#                     'state': 'finance'
#                 })
#             else:
#                 raise UserError(
#                     _('Please confirm If you are the employees manager '))

#     def approve_finance(self):
#         for rec in self:
#             md = False
#             if not rec.purchase_order_id:
#                 for line in rec.cash_line_ids:

#                     total_amount = rec.currency_id._convert(
#                         line.total_price,
#                         self.env.user.company_id.currency_id,
#                         self.env.user.company_id,
#                         fields.Date.today()
#                     )

#                     if total_amount <= 0.00:
#                         raise models.ValidationError(
#                             'Cannot request for zero (0) amounts of money!'
#                         )

#                     if total_amount > line.remaining_budget:
#                         md = True
#             else:
#                 if rec.amount_requested <= 0.00:
#                         raise models.ValidationError(
#                             'Cannot request for zero (0) amounts of money!'
#                         )

#             if md == True:
#                 rec.write({
#                     'state': 'md_approval',
#                 })
#             else:
#                 rec.write({
#                     'state': 'cash_out'
#                 })
#                 rec.approval_date = fields.Date.today()
#                 rec.user = self.env.uid

#         # # Transition method to move to Accountant Approval stage
#         # def submit_for_accountant_approval(self):
#         #     for rec in self:
#         #         rec.state = 'accountant_approval'
#         #         rec.approval_date = fields.Datetime.now()

#         # # Transition method to move to MD Approval stage
#         # def submit_for_md_approval(self):
#         #     for rec in self:
#         #         if rec.state != 'accountant_approval':
#         #             raise ValidationError("Cannot submit for MD approval before Accountant approval!")
#         #         rec.state = 'md_approval'
#         #         rec.approval_date = fields.Datetime.now()

#         # def accountant_cash_out(self):
#         #     for rec in self:
#         #         if rec.state != 'md_approval':
#         #             raise ValidationError("Cannot proceed to Cash Out before MD approval!")
#         #         rec.state = 'cash_out'
#         #         rec.approval_date = fields.Datetime.now()
        
        
#     @api.model_create_multi
#     def create(self, vals_list):
#         result = super().create(vals_list)
#         for res in result:
#             if res.purchase_order_id:
#                 res.purchase_order_id.write({'cash_request_id':res.id})
#         return result


# class CashRequestLines(models.Model):
#     _inherit = 'cash.request.lines'

#     project_id = fields.Many2one(
#         'project.project', string="Project", related='cash_id.project_id', store=True)
#     analytic_account_id = fields.Many2one(
#         'account.analytic.account', string='Analytic Account')

#     budget_id = fields.Many2one('budget.analytic', string="Budget",
#                                 related='cash_id.budget_id', store=True, readonly=False)
#     budget_line_id = fields.Many2one(
#         'budget.line', string="Budget Line",)
#     product_id = fields.Many2one(
#         "product.product", string="Product")
#     cash_id = fields.Many2one('cash.request', string='Order Reference')

#     @api.onchange('budget_id', 'cash_id.budget_id', 'cash_id.project_id')
#     def _onchange_budget_id(self):
#         if self.budget_id:
#             return {'domain': {'budget_line_id': [('budget_analytic_id', '=', self.cash_id.budget_id.id)]}}
#         else:
#             return {'domain': {'budget_line_id': []}}

#     @api.onchange('product_id')
#     def _onchange_product_id(self):
#         """ Automatically set the cost center (account) based on the product's expense account """
#         if self.product_id:
#             # Fetch the expense account from the product
#             self.item = self.product_id.name
#             expense_account = self.product_id.property_account_expense_id or self.product_id.categ_id.property_account_expense_categ_id

#             if expense_account:
#                 self.account_id = expense_account.id
#             else:
#                 self.account_id = False  # Clear the field if no expense account is set

#     remaining_budget = fields.Float(
#         string="Remaining Budget", compute='_compute_remaining_budget', store=True)

#     @api.depends('budget_line_id')
#     def _compute_remaining_budget(self):
#         """ Compute the remaining budget for the selected budget line """
#         for line in self:
#             if line.budget_line_id:
#                 # Assume `achieved_amount` is the amount already spent and `budget_amount` is the budgeted amount
#                 line.remaining_budget = line.budget_line_id.budget_amount - \
#                     line.budget_line_id.achieved_amount
#             else:
#                 line.remaining_budget = 0.0

    # @api.onchange('amount_requested', 'remaining_budget')
    # def _onchange_amount_requested(self):
    #     """ Check if the amount requested exceeds the remaining budget """
    #     if self.total_cost > self.remaining_budget:
    #         return {
    #             'warning': {
    #                 'title': "Warning",
    #                 'message': "The amount requested exceeds the remaining budget."
    #             }
    #         }

    # @api.constrains('amount_requested', 'remaining_budget')
    # def _check_amount_requested(self):
    #     """ Raise an error if the requested amount exceeds the remaining budget """
    #     for line in self:
    #         if line.amount_requested > line.remaining_budget:
    #             raise ValidationError("The amount requested for %s exceeds the remaining budget!" % line.budget_line_id.name)


class ExpenseTypeWizard(models.TransientModel):
    _name = 'expense.type.wizard'
    _description = 'Select Expense Type'

    expense_type = fields.Selection([
        ('purchase_receipt', 'Purchase Receipt'),
        ('vendor_bill', 'Vendor Bill')
    ], string="Expense Type", required=True, default='purchase_receipt')

    cash_requisition_id = fields.Many2one("cash.request", string="Requisition")

    def action_confirm(self):
        """ Handle the confirmed selection of the expense type """
        self.ensure_one()
        cash_request = self.cash_requisition_id

        if self.expense_type == 'purchase_receipt':
            # Logic for creating a purchase receipt
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Receipt',
                'res_model': 'account.move',  # Accounting model for journal entries
                'view_mode': 'form',
                'view_type': 'form',
                # Reference to the account move form view
                'view_id': self.env.ref('account.view_move_form').id,
                'target': 'new',
                'context': {
                    # Type for purchase receipt
                    'default_move_type': 'in_receipt',
                    # Set partner as the requested by user
                    'default_partner_id': cash_request.requested_by.partner_id.id,
                    'default_project_id': cash_request.project_id.id,               # Set the project
                    # Link the cash requisition
                    'default_requisition_id': cash_request.id,
                    'default_invoice_origin': cash_request.name,
                    'default_payment_reference': cash_request.name,
                    # Set the origin as the cash requisition
                    'default_invoice_line_ids': [(0, 0, {'product_id': line.product_id.id if line.product_id else False, 'name': line.description, 'price_unit': line.unit_price, 'quantity': line.qty, 'account_id': line.account_id.id if line.account_id else cash_request._default_account(), 'analytic_distribution': {cash_request.project_id.account_id.id: 100} if cash_request.project_id.account_id else {}}) for line in cash_request.line_ids],
                }
            }
        elif self.expense_type == 'vendor_bill':
            # Logic for creating a vendor bill
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Bill',
                'res_model': 'account.move',  # Accounting model for journal entries
                'view_mode': 'form',
                'view_type': 'form',
                # Reference to the account move form view
                'view_id': self.env.ref('account.view_move_form').id,
                'target': 'new',
                'context': {
                    'default_move_type': 'in_invoice',
                    'default_ref': cash_request.name,  # Set partner as the requested by user
                    'default_project_id': cash_request.project_id.id,               # Set the project
                    # Link the cash requisition
                    'default_requisition_id': cash_request.id,
                    'default_invoice_origin': cash_request.name,
                    # Set the origin as the cash requisition
                    'default_invoice_line_ids': [(0, 0, {'product_id': line.product_id.id if line.product_id else False, 'name': line.description, 'price_unit': line.unit_price, 'quantity': line.qty, 'account_id': line.account_id.id if line.account_id else cash_request._default_account(), 'analytic_distribution': {cash_request.project_id.account_id.id: 100} if cash_request.project_id.account_id else {}}) for line in cash_request.line_ids],
                }
            }

        # return {'type': 'ir.actions.act_window_close'}


class ItemRequest(models.Model):
    _inherit = 'item.requisition'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Pending PM/PC/PE Approval'),
        ('md_approval', 'Pending MD Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    approval_date = fields.Datetime(string="Approval Date", tracking=True)
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')
    sub_task_id = fields.Many2one('project.task', string='Sub Task')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Sales Order Line')
    partner_id = fields.Many2one("res.partner", string="Customer")

    budget_id = fields.Many2one('budget.analytic', string="Budget",
                                domain="[('project_id', '=', project_id)]", tracking=True)
    budget_line_id = fields.Many2one(
        'budget.line', string="Budget Line",)
    product_qty = fields.Float(string="Product Quantity")
    order_line_ids = fields.One2many(
        'item.requisition.order.line', 'order_id', string='Order Lines')
    destination = fields.Many2one('stock.location', string="Destination", domain="[('usage', 'in', ('internal','production','customer','inventory'))]", tracking=True)


    def submit_for_approval(self):
        """Submit the request for approval, routing to MD if quantity exceeds budget"""
        for data in self:
            for line in data.order_line_ids:
                if not line.product_qty or line.product_qty <= 0:
                    raise ValidationError(
                        _("Product quantity must be greater than zero."))

                if line.product_qty > line.remaining_quantity:
                    data.write({
                        'state': 'md_approval'
                    })
                else:
                    data.write({
                        'state': 'submitted'
                    })

    def md_approve(self):
        for rec in self:
            rec.state = 'approved'

    def reject_btn(self):
        for rec in self:
            rec.state = 'rejected'

    @api.onchange("project_id", )
    def onchange_project_id(self,):
        for rec in self:
            if rec.project_id:
                budget = self.env['budget.analytic'].search(
                    [('project_id', '=', rec.project_id.id)], limit=1)
                if budget:
                    rec.budget_id = budget[0].id

                # valid_locations = self.env['stock.location'].search([
                #     ('usage', 'in', ['internal', 'inventory_adjustment']),
                #     ('company_id', 'in', [self.env.context.get('company_id', self.env.user.company_id.id), False])
                # ])
                rec.destination = rec.project_id.location_id.id if rec.project_id.location_id else False
                # if rec.project_id.location_id and rec.project_id.location_id in valid_locations:
                #     rec.destination = rec.project_id.location_id.id
                # else:
                #     rec.destination = False

    def get_default_int_picking_type(self):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', 'in', [self.env.context.get('company_id', self.env.user.company_id.id), False])],
            limit=1).id
    picking_type_id = fields.Many2one(
        "stock.picking.type", default=lambda self: self.get_default_int_picking_type())

    def action_approve_item_requisition(self):
        if self.order_line:
            for data in self:

                if not data.destination:
                    raise models.ValidationError(
                        _("Please provide the destination for the items requested!"))

                pick_obj = self.env["stock.picking"]
                for data in self:

                    move_vals = []
                    for rec in data.order_line:
                        if rec.product_id.is_assembly_line:
                            for item in rec.product_id.assembly_line_ids:
                                move_vals.append([0, 0, {
                                    'name': item.product_id.name,
                                    'product_id': item.product_id.id,
                                    'product_uom_qty': rec.product_qty * item.quantity,
                                    'quantity': rec.product_qty * item.quantity,
                                    'product_uom': item.product_uom_id.id,
                                    'location_dest_id': data.destination.id,
                                    'location_id': data.source.id,
                                    'requisition_id': data.id,
                                    'project_id': data.project_id.id if data.project_id else False,

                                }])
                        else:
                            move_vals.append([0, 0, {
                                'name': '('+str(rec.product_id.name)+') requested from '+str(data.name),
                                'product_id': rec.product_id.id,
                                'product_uom_qty': rec.product_qty,
                                'quantity': rec.product_qty,
                                'product_uom': rec.product_uom.id,
                                'location_dest_id': data.destination.id,
                                'location_id': data.source.id,
                                'requisition_id': data.id,
                                'project_id': data.project_id.id if data.project_id else False,

                            }])

                    pick_values = {
                        'note': 'Items requested by '+str(self.env.user.name),
                        'project_id': data.project_id.id if data.project_id else False,
                        'location_dest_id': data.destination.id,
                        'location_id': data.source.id,
                        'move_ids_without_package': move_vals,
                        'move_type': 'direct',
                        # check correct picking type ID
                        'picking_type_id': data.picking_type_id.id if data.picking_type_id else data.get_default_int_picking_type(),
                        'origin': data.name,
                        'project_id': data.project_id.id,
                        'requisition_id': data.id,

                    }
                    # print(pick_values)
                    pick_id = pick_obj.create(pick_values)

                    pick_id.action_confirm()
                    # pick_id.action_assign()
                    pick_id.button_validate()

                    self.write({'picking_id': pick_id.id})

                data.write({
                    'state': 'done',
                    'user_complete': self.env.uid
                })

            return True

        else:
            raise models.ValidationError(
                _('You must provide atleast one product to complete this request'))

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            budget = self.env['budget.analytic'].search(
                [('project_id', '=', self.project_id.id)], limit=1)
            self.budget_id = budget.id if budget else False
            analytic_account = self.project_id.account_id
            for line in self.order_line:
                line.analytic_account_id = analytic_account.id
                line.budget_id = budget.id if budget else False

    @api.onchange('budget_id')
    def _onchange_budget_id(self):
        if self.budget_id:
            return {'domain': {'budget_line_id': [('budget_analytic_id', '=', self.budget_id.id)]}}
        else:
            return {'domain': {'budget_line_id': []}}


class ItemRequestLines(models.Model):

    _inherit = 'item.requisition.order.line'

    project_id = fields.Many2one(
        'project.project', string="Project", related='order_id.project_id', store=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account')

    budget_id = fields.Many2one('budget.analytic', string="Budget",
                                related='order_id.budget_id', store=True, readonly=False)
    budget_line_id = fields.Many2one(
        'budget.line', string="Budget Line", )
    order_id = fields.Many2one('item.requisition', string='Order Reference')

    @api.onchange('budget_id', 'order_id.budget_id', 'order_id.project_id', 'product_id', 'project_id')
    def _onchange_budget_id(self):
        if self.order_id.budget_id and self.product_id:
            return {'domain': {'budget_line_id': [
                ('budget_analytic_id', '=', self.order_id.budget_id.id),
                #   ('product_id','=',self.product_id.id)
            ]}}
        else:
            # if self.product_id:

            #     return {'domain': {'budget_line_id': [('product_id','=',self.product_id.id)]}}
            # elif self.order_id.budget_id:
            #     return {'domain': {'budget_line_id': [('crossovered_budget_id', '=', self.order_id.budget_id.id)]}}
            # else:
            return {'domain': {'budget_line_id': []}}

    remaining_quantity = fields.Float(
        string="Remaining Quantity", compute="_compute_remaining_quantity", store=True)

    @api.depends('budget_line_id')
    def _compute_remaining_quantity(self):
        """ Compute the remaining quantity for the selected budget line """
        for line in self:
            if line.budget_line_id:
                line.remaining_quantity = line.budget_line_id.quantity - \
                    line.budget_line_id.practical_quantity
            else:
                line.remaining_quantity = 0.0

    @api.constrains('budget_line_id')
    def _check_budget_line_id(self):
        for line in self:
            if not line.budget_line_id and not line.order_id.vehicle_id:
                raise ValidationError(
                    _("A budget line must be selected for each item requisition line.")
                )


class PurchaseRequest(models.Model):
    # _inherit = ['po.requisition', 'mail.activity.mixin']
    _inherit = 'po.requisition'
    _rec_name ="pr_sequence"

    STATUS = [
        ('draft', 'Draft'),
        ('submitted', 'PM Approval'),
        ('procurement_approved', 'Procurement Approval'),
        ('finance_approved', 'Finance Approval'),
        ('md_approval', 'MD Approval'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
    ]
    reject_reason = fields.Text(string="Rejection Reason")
    url = fields.Char("URL", compute="compute_url")

    state = fields.Selection(STATUS, default='draft',
                             tracking=True, index=True)
    approval_date = fields.Datetime(string="Approval Date", tracking=True)

    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')
    sub_task_id = fields.Many2one('project.task', string='Sub Task')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Sales Order Line')
    partner_id = fields.Many2one("res.partner", string="Customer")
    partner_ref = fields.Char("Vendor Reference" ,required=True)


    budget_id = fields.Many2one("budget.analytic", string="Budget", tracking=True)

    department_id = fields.Many2one("hr.department", string="Department ")
    employee_manager_id = fields.Many2one(
        "hr.employee", string="Employee Manager")

    employee_id = fields.Many2one('hr.employee', string="Request Employee",
                                  default=lambda self: self.env.user.employee_id.id if self.env.user.employee_id else False)

    can_approve = fields.Boolean(
        "Can Approve Requisition", compute="compute_can_approve")
    project_manager_id = fields.Many2one(
        'res.users', string="Project Manager",
        domain=lambda self: [('id', 'in', self.env.ref('psi_engineering.group_project_manager').users.ids)]
        )
    # project_manager_id = fields.Many2one(
    #     'res.users', string="Project Manager",
    #     )
    pr_sequence = fields.Char(string="Reference", required=True, copy=False, readonly=True, default='New')
    destination_location_id = fields.Many2one(
        'stock.location', string="Destination Location",
        compute="_compute_destination_location", store=True, readonly=False,required=True
    )
    @api.depends('project_id')
    def _compute_destination_location(self):
        for rec in self:
            rec.destination_location_id = rec.project_id.location_id if rec.project_id else False
      
    
    @api.model
    def create(self, vals):
        if vals.get('pr_sequence', 'New') == 'New':
            vals['pr_sequence'] = self.env['ir.sequence'].next_by_code('po.requisition') or 'New'
        return super(PurchaseRequest, self).create(vals)
    
    def compute_url(self):
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().search(
                [('key', '=', 'web.base.url')], limit=1)
            url = base_url.value + "/web#id=" + \
                str(rec.id)+"&model=po.requisition&view_type=form"
            rec.url = url

    def _get_finance_group_emails(self):
        finance_group_users = self.env.ref('psi_engineering.group_finance').users
        email_list = [user.email for user in finance_group_users if user.email]
        return ",".join(email_list) if email_list else ''
    
    def _get_procurement_group_emails(self):
        procurement_group_users = self.env.ref('psi_engineering.group_procurement').users
        email_list = [user.email for user in procurement_group_users if user.email]
        return ",".join(email_list) if email_list else ''

    def _get_finance_group_emails(self):
        finance_group_users = self.env.ref('psi_engineering.group_finance').users
        email_list = [user.email for user in finance_group_users if user.email]
        return ",".join(email_list) if email_list else ''    
    
    @api.depends('employee_id', 'department_id')
    def compute_can_approve(self):

        for rec in self:
            rec._onchange_employee_id()
            if rec.project_id and rec.project_id.user_id:
                # Check if the current user is the project manager for the project
                if rec.project_id.user_id.id == self.env.user.id:
                    rec.can_approve = True
                else:
                    rec.can_approve = False
            else:
                rec.can_approve = False

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.department_id = rec.employee_id.department_id.id if rec.employee_id.department_id else False
                rec.employee_manager_id = rec.employee_id.parent_id.id if rec.employee_id.parent_id.id else False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """ Automatically set the project manager based on the selected project """
        if self.project_id:
            # if self.project_id.budget_id and self.project_id.budget_id.state != 'confirmed': 
            #     raise UserError("The budget associated with the selected project must be in the 'confirmed' state to proceed.")

            if self.project_id.user_id:
                self.project_manager_id = self.project_id.user_id
            else:
                self.project_manager_id = False    
            
            if self.project_id.budget_id:
                self.budget_id = self.project_id.budget_id.id
                for line in self.order_line:
                    if line.budget_line_id and line.budget_line_id.budget_analytic_id.id != self.project_id.budget_id.id:
                        line.budget_line_id = False
            else:
                for line in self.order_line:
                    line.budget_line_id = False
                self.budget_id = False 

    def submit_order(self):
        for rec in self:
            if rec.project_id:
                if not rec.budget_id:
                    raise UserError("The selected project has no budget associated. Please assign a budget before submitting the order.")
                
                if rec.budget_id.state != 'confirmed':  
                    raise UserError("The budget associated with the selected project is not in the 'confirmed' state. Please confirm the budget before submitting the order.")
                
                rec.state = 'submitted'
                rec.approval_date = datetime.now()
                template_id = self.env.ref('psi_engineering.email_pr_submit_pm')
                if template_id:
                    template_id.send_mail(rec.id, force_send=True)
            else:
                rec.state = 'finance_approved' 
                template_id = self.env.ref('psi_engineering.email_pr_finance')
                if template_id:
                    template_id.send_mail(rec.id, force_send=True)           

    def pm_approval(self):
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError("Funds can only be added after project approval.")
            
            if not rec.project_manager_id:
                raise ValidationError("No project manager is assigned to this project. Please assign one before proceeding.")
            
            if rec.project_id:
                if not rec.budget_id:
                    raise ValidationError("The selected project has no budget associated. Please assign a budget before proceeding.")
                
                if rec.budget_id.state != 'confirmed':  
                    raise ValidationError("The budget associated with the project is not in the 'confirmed' state. Please confirm the budget before proceeding.")
            
            if rec.project_manager_id.id == self.env.user.id or self.env.user.has_group('psi_engineering.group_md'):
                rec.write({
                    'state': 'procurement_approved',
                    'approval_date': datetime.now()
                })
                template_id = self.env.ref('psi_engineering.email_pr_proc')
                if template_id:
                    template_id.send_mail(rec.id, force_send=True)
            else:
                raise ValidationError("Only the Project Manager assigned to this project or the MD can approve the funds.")            

    @api.onchange('budget_id')
    def _onchange_budget_id(self):
        for rec in self:
            if rec.project_id and rec.budget_id:
                if not rec.project_id.budget_id:
                    raise UserError(_("The Project does not have a budget. Consider creating the budget first"))
                if rec.project_id.budget_id and rec.project_id.budget_id.id != rec.budget_id.id:
                    raise UserError(_("Please the budget selected does not belong to the project selected"))            
                   
    def btn_md_approval(self):
        for rec in self:
            rec.write({
                'state': 'approved',
                'user':self.env.user.id,
                'approval_date':fields.Datetime.now()
            })

    def btn_proc_approval(self):
        for rec in self:
            rec.write({
                'state': 'finance_approved',
                'user':self.env.user.id,
                'approval_date':fields.Datetime.now()
            })
            template_id = self.env.ref('psi_engineering.email_pr_finance')
            if template_id:
                template_id.send_mail(rec.id, force_send=True)    

    def submit_md_approval(self):
        for rec in self:
            md_approval = False
            if rec.budget_id :
                for line in rec.order_line.filtered(lambda x: not x.budget_line_id):
                    line.set_budget_line()
                for line in rec.order_line:
                    if not line.budget_line_id:
                        md_approval = True
                    else:
                        remaining_amount = line.budget_line_id.remaining_amount
                        if line.total > remaining_amount:
                            md_approval = True
                    
                
            if md_approval:
                rec.write({
                    'state': 'md_approval'
                })
                template_id = self.env.ref('psi_engineering.email_pr_md_approval')
                if template_id:
                    template_id.send_mail(rec.id, force_send=True)
            else:
                rec.write({
                    'state':'approved',
                    'user':self.env.user.id,
                    'approval_date':fields.Datetime.now()
                })

    def action_approve_po_requisition(self):
        if len(self.order_line2) > 0:
            for rec in self:
                # Basic validation
                if rec.total <= 0:
                    raise UserError(_('Please provide the unit price for the items requested for!'))

                unique_ids = []
                for line_item in self.order_line2:
                    if not line_item.product_id:
                        raise UserError(_('Please Provide products for the PO Requisition'))
                    if not line_item.partner_id:
                        raise UserError(_('Please Add Vendor/Spplier for ' + str(line_item.product_id.name)))

                    # Store vendors as a key-value pair to avoid duplicate vendor entries
                    if not (line_item.partner_id.id in unique_ids):
                        unique_ids.append(line_item.partner_id.id)

                for key in unique_ids:
                    records = self.env['requisition.order.line'].search(
                        [('partner_id', '=', key), ('order_id', '=', rec.id)])
                    picking_type = self.env['stock.picking.type'].search([
                        ('default_location_dest_id', '=', rec.destination_location_id.id),
                        ('code', '=', 'incoming')
                    ], limit=1)  
                    po_data = {
                        'requisition_number': str(rec.name),
                        'date_order': fields.datetime.now(),
                        'partner_id': key,
                        # 'partner_ref': records.partner_ref if len(records) == 1 else ",".join(records.mapped('partner_ref')) if len(records) >1 else "t",
                        'partner_ref': rec.partner_ref,
                        'po_requisition_id': rec.id,
                        'project_id': rec.project_id.id if rec.project_id else False,
                        'project_manager_id': rec.project_id.user_id.id if rec.project_id and rec.project_id.user_id else False,
                        'user_id': rec.create_uid.id,
                        'picking_type_id': picking_type.id if picking_type else False,
                    }

                    if rec.project_id:
                        po_data['budget_id'] = rec.project_id.budget_id.id if rec.project_id.budget_id else False 

                    po_line_list = []
                    for line in records:
                        po_line_data = {
                            'name': line.product_id.product_tmpl_id.name + " " + line.name if line.name else line.product_id.product_tmpl_id.name,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'product_uom': line.product_uom.id,
                            'date_planned': fields.datetime.now(),
                            'price_unit': line.price_unit,
                            'project_id': rec.project_id.id if rec.project_id else False,
                            'budget_line_id': line.budget_line_id.id if line.budget_line_id else False,  # Link budget line
                            'budget_id': rec.project_id.budget_id.id if rec.project_id and rec.project_id.budget_id else False,  # Link to project budget
                        }

                        # Add the analytic distribution (budget line for each product)
                        if rec.project_id and rec.project_id.account_id:
                            po_line_data['analytic_distribution'] = {
                                str(rec.project_id.account_id.id): 100
                            }

                        po_line_list.append([0, False, po_line_data])

                    po_data['order_line'] = po_line_list

                    # Create the PO (Request for Quotation)
                    po_env = self.env['purchase.order'].create(po_data)

                    # Link the purchase order to the requisition order lines
                    for line in records:
                        line.write({'purchase_order_id': po_env.id})

                    # Update the requisition state
                    rec.write({
                        'state': 'done',
                        'user_complete': self.env.uid,
                        'purchase_order': po_env.id,
                    })

            return True



    def cancel_order(self):
        for rec in self:
            rec.state = 'cancel'

    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'        

    def action_reject(self):
        """Open a wizard to enter the rejection reason before rejecting the PO."""
        return {
            'name': 'Reject Purchase Request',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_request_id': self.id},
        }
        


class PurchaseRequestLines(models.Model):

    _inherit = 'requisition.order.line'

    project_id = fields.Many2one(
        'project.project', string="Project", related='order_id.project_id', store=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account')

    budget_id = fields.Many2one('budget.analytic', string="Budget",
                                related='order_id.budget_id', store=True, readonly=False)
    budget_line_id = fields.Many2one(
        'budget.line', string="Budget Line", )
    remaining_amount = fields.Float("Remaining Amount")

    partner_id = fields.Many2one(
        'res.partner', string='Vendor',
        domain="[('is_vendor', '=', True), ('state', '=', 'approved')]",
        required=True
    )
    pr_sequence = fields.Integer('Sequence', default=10)

    product_id = fields.Many2one('product.product', string="Product", required=True)
    price_unit = fields.Float("Unit Price",store=True,readonly=False)

    product_domain = fields.Char("Product Domain", compute="compute_product_domain", store=False)
    @api.onchange("budget_id","project_id","order_id.budget_id")
    def compute_product_domain(self):
        """Update domain for product_id based on budget lines."""
        for rec in self:
            if rec.budget_id:
                # Assuming budget.line has a product_id field
                budget_lines = self.env["budget.line"].search([("budget_analytic_id", "=", self.budget_id.id)])
                product_ids = budget_lines.mapped("product_id").ids
                
                domain = [("id", "in", product_ids)]
                rec.product_domain = json.dumps(domain)
            else:
                rec.product_domain = json.dumps([])

    show_budget_warning = fields.Boolean("Show Budget Warning", compute="compute_show_budget_warning", store=True)

    @api.depends('state','total','budget_line_id')
    def compute_show_budget_warning(self):
        for rec in self:
            if not rec.budget_line_id:
                rec.show_budget_warning = False
            elif rec.total > rec.budget_line_id.remaining_amount:
                rec.show_budget_warning = True
            else:
                rec.show_budget_warning = False          
          
    @api.onchange('state')
    def _force_budget_warning_compute(self):
        for rec in self:
            rec._compute_show_budget_warning()
            
    def set_budget_line(self):
        for line in self:
            if line.product_id and line.order_id.budget_id:
                budget_line = line.order_id.budget_id.budget_line_ids.filtered(lambda x:x.product_id and x.product_id.id == line.product_id.id)
                if budget_line:
                    line.write({
                        'remaining_amount': budget_line[0].remaining_amount,
                        'budget_line_id': budget_line[0].id,
                    })

    @api.onchange('budget_id', 'order_id.budget_id', 'order_id.project_id', 'product_id', 'project_id')
    def _onchange_budget_id(self):
        if self.order_id.budget_id and self.product_id:
            return {'domain': {'budget_line_id': [('budget_analytic_id', '=', self.order_id.budget_id.id), ('product_id', '=', self.product_id.id)]}}
        else:
            if self.product_id:

                return {'domain': {'budget_line_id': [('product_id', '=', self.product_id.id)]}}
            elif self.order_id.budget_id:
                return {'domain': {'budget_line_id': [('budget_analytic_id', '=', self.order_id.budget_id.id)]}}
            else:
                return {'domain': {'budget_line_id': []}}

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.price_unit = record.product_id.standard_price
            else:
                record.price_unit = 0.0 

class ProjectProject(models.Model):
    _inherit = 'project.project'
    _rec_name = "project_name"

    date_start = fields.Date("Expected Start Date")
    budget_id = fields.Many2one("budget.analytic", string="Project Budget ")
    date_end = fields.Date("Expectd End Date")
    site_id = fields.Char("Site ID")
    site_name = fields.Char("Site Name")
    material_ids = fields.One2many(
        'task.material', 'project_id', string="Materials")
    labour_ids = fields.One2many(
        "task.labour", "project_id", string="Labour Costs")
    overhead_ids = fields.One2many(
        "task.overhead", "project_id", string="Overhead Costs")
    # product_specification_ids = fields.Many2many(
    #     'product.specification', 'project_product_specification_rel', 'project_id', 'specification_id', string='Product Specifications')
    product_specification_id = fields.Many2one(
        "product.specification", string="Product specification")
    total_material_cost = fields.Float(
        string="Total Material Cost", compute='_compute_total_material_cost', store=True)
    total_labour_cost = fields.Float(
        string="Total Labour Cost", compute='_compute_total_labour_cost', store=True)
    total_overhead_cost = fields.Float(
        string="Total Overhead Cost", compute='_compute_total_overhead_cost', store=True)
    total_estimated_cost = fields.Float(
        string="Total Estimated Cost", compute='_compute_total_estimated_cost', store=True)

    cash_request_count = fields.Integer(
        string='Cash Requests', compute='_compute_cash_request_count')
    project_name = fields.Char("Project Name")
    expense_count = fields.Integer("Expense Count", compute="compute_expense_count")

    
    def action_create_purchase_order(self):
        """Return action to open the cash request form with prefilled values."""
        self.ensure_one()

        
        
        return {
            'name': 'Create Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            # Reference to your form view
            'view_id': self.env.ref('purchase.purchase_order_form').id,
            'target': 'current',  # Opens in a new window
            'context': {
                'default_project_id': self.id,
                'default_budget_id':self.budget_id.id if self.budget_id else False
                
            },
        }
    purchase_order_count = fields.Integer(
        string='Purchase Orders',
        compute='_compute_purchase_order_count'
    )
    def action_view_expenses(self):
        for rec in self:
            return {
                'name':"Expenses",
                'res_model': "hr.expense",
                'view_mode':'list,form',
                'domain':[('project_id','=',rec.id)],
                'type':'ir.actions.act_window',
                'context':{'default_project_id':rec.id},
                'target':'current',
            }
            
    
    def compute_expense_count(self):
        for rec in self:
            rec.expense_count = self.env['hr.expense'].search_count([('project_id','=',rec.id)])

    def add_expenses(self):
        for record in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'EXpense',
                'res_model': 'hr.expense',
                'view_mode': 'form',
                'view_id':self.env.ref('hr_expense.hr_expense_view_form').id,
                'target': 'new',  
                'context': {
                    'default_project_id': record.id
                },
            }
    
    def _compute_purchase_order_count(self):
        for task in self:
            task.purchase_request_count = self.env['purchase.order'].search_count(
                [('project_id', '=', task.id)])
            
    def action_view_purchase_orders(self):
        for task in self:
            return {
                'name':"Project Purchase Orders",
                'res_model':"purchase.order",
                'view_mode':'list,form',
                'type':'ir.actions.act_window',
                'target':'current',
                'domain':[('project_id','=', task.id)],
                'context':{'default_project_id':task.id,'default_budget_id':task.budget_id.id if task.budget_id else False}
            }

    # @api.depends('site_id', 'site_name')
    @api.onchange('site_id', 'site_name')
    def _compute_site_name(self):
        for rec in self:
            names = []
            if rec.site_id:
                names.append(rec.site_id)
            if rec.site_name:
                names.append(rec.site_name)

            rec.project_name = " - ".join(names)
            rec.name = " - ".join(names)

    @api.onchange('name', 'project_name', 'site_id', 'site_name')
    def _update_location_name(self):
        for rec in self:
            if rec.project_name:
                rec.location_id.write({
                    'name': rec.project_name
                })

    @api.depends('material_ids.total_cost')
    def _compute_total_material_cost(self):
        """Compute the total material cost for the project."""
        for project in self:
            project.total_material_cost = sum(
                material.total_cost for material in project.material_ids)

    @api.depends('labour_ids.total_cost')
    def _compute_total_labour_cost(self):
        """Compute the total labor cost for the project based on its labor records."""
        for project in self:
            project.total_labour_cost = sum(
                labour.total_cost for labour in project.labour_ids)

    @api.depends('overhead_ids.total_overhead_cost')
    def _compute_total_overhead_cost(self):
        """Compute the total overhead cost for the project based on its overhead records."""
        for project in self:
            project.total_overhead_cost = sum(
                overhead.total_overhead_cost for overhead in project.overhead_ids)

    @api.depends('total_material_cost', 'total_labour_cost', 'total_overhead_cost')
    def _compute_total_estimated_cost(self):
        """Compute the total estimated cost for the project."""
        for project in self:
            project.total_estimated_cost = project.total_material_cost + \
                project.total_labour_cost + project.total_overhead_cost

    def _compute_cash_request_count(self):
        for project in self:
            project.cash_request_count = self.env['cash.request'].search_count(
                [('project_id', '=', project.id)])

    def action_view_cash_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_cash_request').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        return action

    def action_view_project_budget(self):
        """Return action to view project budget related to the project."""
        return {
            'name': self.budget_id.name,
            'res_model': "budget.analytic",
            'res_id': self.budget_id.id,
            'view_mode': "form",
            'view_id': self.env.ref("account_budget.view_budget_analytic_form").id,
            'type': "ir.actions.act_window",
            'target': 'current',
            'context': {'create': False, 'delete': False, },
        }

    def action_view_project(self):
        """Return action to view project budget related to the project."""
        return {
            'name': self.display_name,
            'res_model': "project.project",
            'res_id': self.id,
            'view_mode': "form",
            'view_id': self.env.ref("project.edit_project").id,
            'type': "ir.actions.act_window",
            'target': 'current',
            'context': {'create': False, 'delete': False, },
        }

    item_request_count = fields.Integer(
        string='Material Internal Pickups',
        compute='_compute_item_request_count'
    )

    def _compute_item_request_count(self):
        for task in self:
            task.item_request_count = self.env['item.requisition'].search_count(
                [('project_id', '=', task.id)])

    def action_view_item_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_item_request').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        return action
    purchase_request_count = fields.Integer(
        string='Purchase Requests',
        compute='_compute_purchase_request_count'
    )

    def _compute_purchase_request_count(self):
        for task in self:
            task.purchase_request_count = self.env['po.requisition'].search_count(
                [('project_id', '=', task.id)])

    def action_view_purchase_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_purchase_request').read()[0]
        action['domain'] = [('project_id', '=', self.id)]
        return action

    purchase_receipt_count = fields.Integer(
        compute='_compute_purchase_receipt_count')

    def _compute_purchase_receipt_count(self):
        for project in self:
            receipts = self.env['account.move'].search(
                [('project_id', '=', project.id), ('move_type', '=', 'in_receipt')])
            project.purchase_receipt_count = len(receipts)

    def action_view_purchase_receipts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Receipts',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('project_id', '=', self.id), ('move_type', '=', 'in_receipt')],
            'context': {'create': False},
        }

    location_id = fields.Many2one(
        'stock.location', string="Location", readonly=True)

    # @api.model_create_multi
    # def create(self, vals):
    #     # Call the original create method to create the project
    #     projects = super(ProjectProject, self).create(vals)

    #     # Create a corresponding stock location
    #     for project in projects:
    #         location_vals = {
    #             'name': project.name,
    #             'project_id': project.id,
    #             'project_location': True,
    #             'usage': 'internal',   # Define the usage type for the location
    #         }
    #         location = self.env['stock.location'].create(location_vals)

    #         inventory = self.env['stock.location'].search([('usage','=','inventory')],limit=1)
    #         warehouse = self.env['stock.warehouse'].search([('company_id','=', self.env.company.id)],limit=1)
    #         # Link the newly created location with the project
    #         project.location_id = location.id
    #         operation_types = [
    #         {'name': f"{project.name} Receipts", 'code': 'incoming', 
    #          'default_location_dest_id': project.location_id.id, 'project_id': project.id},
    #         {'name': f"{project.name} Consumption", 'code': 'outgoing', 
    #          'default_location_src_id': project.location_id.id, 
    #          'default_location_dest_id': inventory.id, 'project_id': project.id},
    #         {'name': f"{project.name} Internal Transfer", 'code': 'internal', 
    #          'default_location_src_id': warehouse.lot_stock_id.id, 
    #          'default_location_dest_id': project.location_id.id, 'project_id': project.id},
    #         # {'name': f"{project.name} Returns", 'code': 'return', 
    #         #  'default_location_src_id': project.location_id.id, 
    #         #  'default_location_dest_id': self.env.ref('stock.stock_location_customers').id, 'project_id': project.id},
    #         ]

    #         for op_type in operation_types:
    #             self.env['stock.picking.type'].create(op_type)

        

    #     return projects

    def create(self, vals):
        # Call the original create method to create the project
        projects = super(ProjectProject, self).create(vals)

        for project in projects:
            # Create a corresponding stock location
            

            # Get inventory location and warehouse
            inventory = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
            location_vals = {
                'name': project.name,
                'project_id': project.id,
                'location_id':warehouse.view_location_id.id,
                'project_location': True,
                'usage': 'internal',
            }
            location = self.env['stock.location'].create(location_vals)
            # Link the newly created location with the project
            project.location_id = location.id

            # Define operation types with unique sequence codes
            operation_types = [
                {
                    'name': f"{project.name} Receipts",
                    'code': 'incoming',
                    'sequence_code': f"IN-{project.site_id}" if project.site_id else f"IN-{project.id}",
                    'default_location_dest_id': project.location_id.id,
                    'project_id': project.id,
                },
                {
                    'name': f"{project.name} Consumption",
                    'code': 'outgoing',
                    'sequence_code': f"CONS-{project.site_id}" if project.site_id else f"CONS-{project.id}",
                    'default_location_src_id': project.location_id.id,
                    'default_location_dest_id': inventory.id,
                    'project_id': project.id,
                },
                {
                    'name': f"{project.name} Internal Transfer",
                    'code': 'internal',
                    'sequence_code': f"INT-{project.site_id}" if project.site_id else f"INT-{project.id}",
                    'default_location_src_id': warehouse.lot_stock_id.id,
                    'default_location_dest_id': project.location_id.id,
                    'project_id': project.id,
                },
                {
                    'name': f"{project.name} Deliveries",
                    'code': 'outgoing',
                    'sequence_code': f"OUT-{project.site_id}" if project.site_id else f"OUT-{project.id}",
                    'default_location_src_id': project.location_id.id,
                    'default_location_dest_id': self.env.ref('stock.stock_location_customers').id,
                    'project_id': project.id,
                },
            ]

            # Create operation types
            for op_type in operation_types:
                self.env['stock.picking.type'].create(op_type)

        return projects

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    project_id = fields.Many2one(
        'project.project', 
        string='Project',
        help='Select a related project for this picking type.'
    )

class ProjectTask(models.Model):
    _inherit = 'project.task'

    material_ids = fields.One2many(
        'task.material', 'parent_task_id', string="Materials")
    material_child_ids = fields.One2many(
        'task.material', 'task_id', string="Materials")
    total_material_cost = fields.Float(
        string="Total Material Cost", compute='_compute_total_material_cost')
    
    is_milestone = fields.Boolean(string="Is Milestone task", help="Check if this task is a milestone")

    @api.model
    def send_task_milestone_reminders(self):
        """Send email reminders for tasks and milestones due today."""
        today = fields.Date.context_today(self)

        tasks = self.env['project.task'].search([
            ('date_deadline', '=', today),
            ('is_milestone', '=', True),
            ('stage_id.fold', '=', False) 
        ])

        project_manager_group = self.env.ref('psi_engineering.group_project_manager')
        project_manager_emails = project_manager_group.users.mapped('email')

        for task in tasks:
            # Determine email subject and message
            subject = "Task Milestone Due Today"
            message_body = f"Reminder: The task **{task.name}** is due today!"

            recipient_emails = list(filter(None, [task.user_id.email] + project_manager_emails))  # Remove None values

            if recipient_emails:
                # Send email
                mail_values = {
                    'subject': subject,
                    'body_html': f"<p>{message_body}</p>",
                    'email_to': ",".join(recipient_emails),
                }
                self.env['mail.mail'].create(mail_values).send()


    @api.depends('material_ids.total_cost')
    def _compute_total_material_cost(self):
        """Compute the total material cost for the project."""
        for project in self:
            project.total_material_cost = sum(
                material.total_cost for material in project.material_ids)

    labour_ids = fields.One2many(
        'task.labour', 'parent_task_id', string="Labour Costs")
    labour_child_ids = fields.One2many(
        'task.labour', 'task_id', string="Labour Costs")
    total_labour_cost = fields.Float(
        string="Total Labour Cost", compute='_compute_total_labour_cost', store=True)

    @api.depends('labour_ids.total_cost')
    def _compute_total_labour_cost(self):
        """Compute the total labor cost for the task."""
        for task in self:
            task.total_labour_cost = sum(
                labour.total_cost for labour in task.labour_ids)

    overhead_ids = fields.One2many(
        'task.overhead', 'parent_task_id', string="Overhead Costs")
    overhead_child_ids = fields.One2many(
        'task.overhead', 'task_id', string="Overhead Costs")
    total_overhead_cost = fields.Float(
        string="Total Overhead Cost", compute='_compute_total_overhead_cost', store=True)

    @api.depends('overhead_ids.amount', 'overhead_child_ids.amount')
    def _compute_total_overhead_cost(self):
        """Compute the total overhead cost for the task."""
        for task in self:
            task.total_overhead_cost = sum(overhead.amount for overhead in task.overhead_ids) + \
                sum(overhead.amount for overhead in task.overhead_child_ids)
    # cash_request_count = fields.Integer(
    #     string='Cash Requests',
    #     compute='_compute_cash_request_count'
    # )
    
    cash_request_count = fields.Integer(
        string='Cash Requests'
    )

    total_estimated_cost = fields.Float(
        string="Total Estimated Cost", compute='_compute_total_estimated_cost', store=True)

    @api.depends('estimated_costs_ids.total_cost')
    def _compute_total_estimated_cost(self):
        """Compute the total estimated cost for the task."""
        for task in self:
            task.total_estimated_cost = sum(
                cost.total_cost for cost in task.estimated_costs_ids)

    # def _compute_cash_request_count(self):
    #     for task in self:
    #         task.cash_request_count = self.env['cash.request'].search_count(
    #             [('task_id', '=', task.id)])

    def action_view_cash_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_cash_request').read()[0]
        action['domain'] = [('task_id', '=', self.id)]
        return action
    item_request_count = fields.Integer(
        string='Item Requests',
        compute='_compute_item_request_count'
    )

    def _compute_item_request_count(self):
        for task in self:
            task.item_request_count = self.env['item.requisition'].search_count(
                [('task_id', '=', task.id)])

    def action_view_item_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_item_request').read()[0]
        action['domain'] = [('task_id', '=', self.id)]
        return action
    purchase_request_count = fields.Integer(
        string='Purchase Requests',
        compute='_compute_purchase_request_count'
    )

    def _compute_purchase_request_count(self):
        for task in self:
            task.purchase_request_count = self.env['po.requisition'].search_count(
                [('task_id', '=', task.id)])

    project_type_id = fields.Many2one("project.type",  store=True)
    milestone_template_id = fields.Many2one(
        'project.milestone.template',
        string="Milestone Template",
        tracking=True,
        # domain="[('project_type_id','=',project_type_id)]",
        help="Select the milestone template associated with this project milestone."
    )
    checklist_ids = fields.One2many(
        'project.milestone.checklist',
        'task_id',
        string="Checklists"
    )

    image_ids = fields.One2many(
        'project.milestone.images',
        'task_id',
        string="Task Milestone Images"
    )

    attachment_ids = fields.Many2many(
        'ir.attachment', string="Milestone Attachments")
    checklist_completed = fields.Boolean(
        "Check list Completed", tracking=True,)
    checklist_completed_by = fields.Many2one(
        "res.users", string="Checklist Completed By", tracking=True,)
    receipt_printed = fields.Boolean(string="Receipt Printed", default=False)

    # Define the states
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('in_progress', 'In Progress'),
    #     ('completed', 'Completed'),
    # ], string="State", default='draft', tracking=True)

    # Actions to change states
    # def action_start(self):
    #     """Set the milestone state to 'In Progress'."""
    #     self.state = 'in_progress'

    def action_complete(self):
        """Set the milestone state to 'Completed'."""
        if self.milestone_template_id:
            if len(self.checklist_ids.filtered(lambda x: not x.display_type and x.answer_type == 'pass_fail' and not x.answer_pass_fail)) > 0:
                raise UserError(
                    'Please first Complete the Check List before Completing the Milestone')
            if len(self.checklist_ids.filtered(lambda x: not x.display_type and x.answer_type == 'number' and x.answer_number == 0)) > 0:
                raise UserError(
                    'Please first Complete the Check List before Completing the Milestone')
            if len(self.checklist_ids.filtered(lambda x: not x.display_type and x.answer_type == 'text' and not x.answer_text)) > 0:
                raise UserError(
                    'Please first Complete the Check List before Completing the Milestone')
        self.state = 'completed'
        self.is_reached = True

    def action_reset_to_draft(self):
        """Reset the milestone state to 'Draft'."""
        self.state = 'draft'

    @api.onchange('milestone_template_id')
    def _onchange_milestone_template_id(self):
        if self.milestone_template_id:
            self.checklist_ids = [(5, 0, 0)]
            checklist_items = []
            for item in self.milestone_template_id.milestone_item_ids:
                checklist_items.append((0, 0, {
                    'no': item.no,
                    'name': item.name,
                    'display_type': item.display_type,
                    'answer_type': item.answer_type,
                    'comments': item.comments or '',
                    'milestone_template_id': self.milestone_template_id.id,
                    'project_id': self.project_id.id if self.project_id else False,
                    'project_type_id': self.project_type_id.id if self.project_type_id else False,
                }))
            self.checklist_ids = checklist_items

    def create_checklists_from_template(self):
        """Creates checklists based on the selected template"""
        if self.milestone_template_id:
            self.checklist_ids = [(5, 0, 0)]
            checklist_items = []
            for item in self.milestone_template_id.milestone_item_ids:
                checklist_items.append((0, 0, {
                    'no': item.no,
                    'name': item.name,
                    'display_type': item.display_type,
                    'answer_type': item.answer_type,
                    'comments': item.comments or '',
                    'milestone_template_id': self.milestone_template_id.id,
                    'project_id': self.project_id.id if self.project_id else False,
                    'project_type_id': self.project_type_id.id if self.project_type_id else False,
                }))
            self.checklist_ids = checklist_items

    def action_redirect_to_website_form(self):
        """Redirects the user to the website form for filling in milestone data."""
        # Generate the URL to the website form
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        # Assuming the milestone form URL includes project id
        website_url = f"{base_url}/milestone/checklist/{self.id}"

        return {
            'type': 'ir.actions.act_url',
            'url': website_url,
            'target': 'new',  # Opens the form in a new tab
        }

    def view_milestone(self,):
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'project.milestone',
            'view_mode': 'form',
            'view_id': self.env.ref('project.project_milestone_view_form').id,
            'target': 'current',
            'res_id': self.id,
            'context': {
                'default_project_id': self.project_id.id,
                'default_project_type_id': self.project_type_id.id if self.project_type_id else False
            },
        }

    def action_view_purchase_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_purchase_request').read()[0]
        action['domain'] = [('task_id', '=', self.id)]
        return action

    def action_create_cash_request(self):
        """Return action to open the cash request form with prefilled values."""
        self.ensure_one()

        # Find the related project, customer, and sale order if available
        project = self.project_id
        customer = project.partner_id if project.partner_id else False
        sale_order = project.sale_order_id if hasattr(
            project, 'sale_order_id') else False
        sale_order_line = project.sale_line_id if hasattr(
            project, 'sale_line_id') else False
        # Return action to open the cash request form view with prefilled fields
        return {
            'name': 'Create Cash Request',
            'type': 'ir.actions.act_window',
            'res_model': 'cash.request',
            'view_mode': 'form',
            # Reference to your form view
            'view_id': self.env.ref('requisitions.cash_requisition_form').id,
            'target': 'new',  # Opens in a new window
            'context': {
                'default_task_id': self.id,
                'default_project_id': project.id if project else False,
                'default_partner_id': customer.id if customer else False,
                'default_sale_order_id': sale_order.id if sale_order else False,
                'default_sale_order_line_id': sale_order_line.id if sale_order_line else False
            },
        }

    def action_create_item_request(self):
        """Return action to open the cash request form with prefilled values."""
        self.ensure_one()

        # Find the related project, customer, and sale order if available
        project = self.project_id
        customer = project.partner_id if project.partner_id else False
        sale_order = project.sale_order_id if hasattr(
            project, 'sale_order_id') else False
        sale_order_line = project.sale_line_id if hasattr(
            project, 'sale_line_id') else False
        # Return action to open the cash request form view with prefilled fields
        return {
            'name': 'Create Material Internal Pickups',
            'type': 'ir.actions.act_window',
            'res_model': 'item.requisition',
            'view_mode': 'form',
            # Reference to your form view
            'view_id': self.env.ref('requisitions.item_requisition_form').id,
            'target': 'new',  # Opens in a new window
            'context': {
                'default_task_id': self.id,
                'default_project_id': project.id if project.partner_id else False,
                'default_partner_id': customer.id if customer else False,
                'default_sale_order_id': sale_order.id if sale_order else False,
                'default_sale_order_line_id': sale_order_line.id if sale_order_line else False
            },
        }

    def action_create_purchase_request(self):
        """Return action to open the cash request form with prefilled values."""
        self.ensure_one()

        # Find the related project, customer, and sale order if available
        project = self.project_id
        customer = project.partner_id if project.partner_id else False
        sale_order = project.sale_order_id if hasattr(
            project, 'sale_order_id') else False
        sale_order_line = project.sale_line_id if hasattr(
            project, 'sale_line_id') else False
        # Return action to open the cash request form view with prefilled fields
        return {
            'name': 'Create Purchase Requisition',
            'type': 'ir.actions.act_window',
            'res_model': 'po.requisition',
            'view_mode': 'form',
            # Reference to your form view
            'view_id': self.env.ref('requisitions.po_requisition_form').id,
            'target': 'new',  # Opens in a new window
            'context': {
                'default_task_id': self.id,
                'default_project_id': project.id if project else False,
                'default_partner_id': customer.id if customer else False,
                'default_sale_order_id': sale_order.id if sale_order else False,
                'default_sale_order_line_id': sale_order_line.id if sale_order_line else False
            },
        }
        
    def action_create_purchase_order(self):
        """Return action to open the cash request form with prefilled values."""
        self.ensure_one()

        # Find the related project, customer, and sale order if available
        project = self.project_id
        
        return {
            'name': 'Create Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            # Reference to your form view
            'view_id': self.env.ref('purchase.purchase_order_form').id,
            'target': 'new',  # Opens in a new window
            'context': {
                'default_project_id': project.id if project else False,
                'default_task_id':self.id,
                'default_budget_id':project.budget_id.id if project.budget else False
                
            },
        }
    purchase_order_count = fields.Integer(
        string='Purchase Orders',
        compute='_compute_purchase_order_count'
    )
    
    def _compute_purchase_order_count(self):
        for task in self:
            task.purchase_order_count = self.env['purchase.order'].search_count(
                [('task_id', '=', task.id)])
            
    def action_view_purchase_orders(self):
        for task in self:
            return {
                'name':"Project Purchase Orders",
                'res_model':"purchase.order",
                'view_mode':'list,form',
                'type':'ir.actions.act_window',
                'target':'current',
                'domain':[('task_id','=', task.id)],
                'context':{'default_task_id':task.id,'default_project_id':task.project_id.id,'default_budget_id':task.project_id.budget_id.id if task.project_id.budget_id else False}
            }

    material_costs_ids = fields.One2many(
        'material.costs', 'task_id', string="Material Costs")
    labour_costs_ids = fields.One2many(
        'labour.costs', 'task_id', string="Labour Costs")
    overhead_costs_ids = fields.One2many(
        'overhead.costs', 'task_id', string="Overhead Costs")
    estimated_costs_ids = fields.One2many(
        'estimated.costs', 'task_id', string="Estimated Costs")

    amount_total_material_costs = fields.Float(
        string="Total Material Costs", compute='_compute_total_material_costs')
    amount_total_labour_costs = fields.Float(
        string="Total Labour Costs", compute='_compute_total_labour_costs')
    amount_total_overhead_costs = fields.Float(
        string="Total Overhead Costs", compute='_compute_total_overhead_costs')
    amount_total_estimation_cost = fields.Float(
        string="Total Estimated Costs", compute='_compute_total_estimation_costs')

    @api.depends('material_costs_ids.total_cost')
    def _compute_total_material_costs(self):
        for task in self:
            task.amount_total_material_costs = sum(
                cost.total_cost for cost in task.material_costs_ids)

    @api.depends('labour_costs_ids.total_cost')
    def _compute_total_labour_costs(self):
        for task in self:
            task.amount_total_labour_costs = sum(
                cost.total_cost for cost in task.labour_costs_ids)

    @api.depends('overhead_costs_ids.total_overhead_cost')
    def _compute_total_overhead_costs(self):
        for task in self:
            task.amount_total_overhead_costs = sum(
                cost.total_overhead_cost for cost in task.overhead_costs_ids)

    @api.depends('estimated_costs_ids.total_cost')
    def _compute_total_estimation_costs(self):
        for task in self:
            task.amount_total_estimation_cost = sum(
                cost.total_cost for cost in task.estimated_costs_ids)


class TaskMaterial(models.Model):
    _name = 'task.material'
    _description = 'Materials for Task'
    _order = "create_date desc"
    _rec_name = "product_id"

    task_id = fields.Many2one(
        'project.task', string="Task", required=True, ondelete='cascade')
    parent_task_id = fields.Many2one('project.task', string="Parent Task", )
    product_id = fields.Many2one(
        'product.product', string="Material", required=True, domain=[('type', '=', 'service')])
    quantity = fields.Float(string="Quantity", required=True, default=1.0)
    uom_id = fields.Many2one(
        'uom.uom', string="Unit of Measure", required=True)
    unit_price = fields.Float(string="Unit Price", required=True)
    total_cost = fields.Float(
        string="Total Cost", compute='_compute_total_cost', store=True)
    currency_id = fields.Many2one(
        'res.currency', string="Currency", default=lambda self: self.env.company.currency_id.id)
    project_id = fields.Many2one(
        "project.project", string="Project", related="task_id.project_id", store=True)
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        """Compute the total cost based on quantity and unit price."""
        for record in self:
            record.total_cost = record.quantity * record.unit_price

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        """Ensure UoM belongs to the product's UoM category."""
        if self.product_id and self.uom_id and self.uom_id.category_id != self.product_id.uom_id.category_id:
            self.uom_id = False
            return {
                'warning': {
                    'title': "Invalid UoM",
                    'message': "The selected Unit of Measure must belong to the same category as the product's UoM."
                }
            }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set the unit price to the cost price of the selected product and set UoM from the product."""
        if self.product_id:
            self.unit_price = self.product_id.standard_price
            # Fetch the default unit of measure from the product
            self.uom_id = self.product_id.uom_id.id
            return {'domain': {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for res in res_list:
            if res.task_id:
                if res.task_id.parent_id:

                    if not res.project_id and res.task_id.parent_id.project_id:
                        res.task_id.write({
                            'project_id': res.task_id.parent_id.project_id.id
                        })

        return res_list


class TaskLabour(models.Model):
    _name = 'task.labour'
    _description = 'Labor Costs for Task'
    _order = "create_date desc"

    name = fields.Char("Description")
    task_id = fields.Many2one(
        'project.task', string="Task", required=True, ondelete='cascade')
    parent_task_id = fields.Many2one('project.task', string="Parent Task", )
    project_id = fields.Many2one('project.project', string="Project",
                                 related="task_id.project_id", store=True, readonly=True)
    number_of_people = fields.Integer(
        string="Number of People", required=True, default=1)
    rate_per_day = fields.Float(string="Rate per Day", required=True)
    number_of_days = fields.Float(
        string="Number of Days", required=True, default=1)
    total_cost = fields.Float(
        string="Total Labor Cost", compute='_compute_total_cost', store=True)
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")

    @api.depends('number_of_people', 'rate_per_day', 'number_of_days')
    def _compute_total_cost(self):
        """Compute the total labor cost based on the number of people, rate per day, and number of days."""
        for record in self:
            record.total_cost = record.number_of_people * \
                record.rate_per_day * record.number_of_days

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for res in res_list:
            if res.task_id:
                if res.task_id.parent_id:
                    if not res.project_id and res.task_id.parent_id.project_id:
                        res.task_id.write({
                            'project_id': res.task_id.parent_id.project_id.id
                        })
        return res_list


class TaskOverhead(models.Model):
    _name = 'task.overhead'
    _description = 'Overhead Costs for Task'

    task_id = fields.Many2one(
        comodel_name='project.task', string="Task", required=True, ondelete='cascade')
    parent_task_id = fields.Many2one('project.task', string="Parent Task")
    project_id = fields.Many2one(
        'project.project', string="Project", related="task_id.project_id", store=True)
    description = fields.Char(string="Description", required=True)
    amount = fields.Float(string="Amount", required=True)
    total_overhead_cost = fields.Float(
        string="Total Overhead Cost", compute='_compute_total_overhead_cost', store=True)
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")
    quantity = fields.Float("Quantity")

    @api.depends('amount', 'quantity')
    def _compute_total_overhead_cost(self):
        """Compute the total overhead cost."""
        for record in self:
            record.total_overhead_cost = record.amount

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for res in res_list:
            if res.task_id:
                if res.task_id.parent_id:
                    if not res.project_id and res.task_id.parent_id.project_id:
                        res.task_id.write({
                            'project_id': res.task_id.parent_id.project_id.id
                        })
        return res_list


class TaskEstimatedCosts(models.Model):
    _name = 'task.estimatedcosts'
    _description = 'Estimation Costs for Task'

    task_id = fields.Many2one(
        'project.task', string="Task", required=True, ondelete='cascade')
    parent_task_id = fields.Many2one('project.task', string="Parent Task",)
    project_id = fields.Many2one(
        'project.project', string="Project", related="task_id.project_id", store=True)
    description = fields.Char(string="Description", required=True)
    amount = fields.Float(string="Amount", required=True)
    total_estimation_cost = fields.Float(
        string="Total Estmation Cost", compute='_compute_total_overhead_cost', store=True)
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")

    @api.depends('amount')
    def _compute_total_overhead_cost(self):
        """Compute the total estimation cost."""
        for record in self:
            record.total_estimation_cost = record.amount

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for res in res_list:
            if res.task_id:
                if res.task_id.parent_id:
                    if not res.project_id and res.task_id.parent_id.project_id:
                        res.task_id.write({
                            'project_id': res.task_id.parent_id.project_id.id
                        })
        return res_list


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cash_request_count = fields.Integer(
        string='Cash Requests'
    )
    
    # cash_request_count = fields.Integer(
    #     string='Cash Requests',
    #     compute='_compute_cash_request_count'
    # )

    # def _compute_cash_request_count(self):
    #     for order in self:
    #         order.cash_request_count = self.env['cash.request'].search_count(
    #             [('sale_order_id', '=', order.id)])

    def action_view_cash_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_cash_request').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        return action

    item_request_count = fields.Integer(
        string='Item Requests',
        compute='_compute_item_request_count'
    )

    def _compute_item_request_count(self):
        for task in self:
            task.item_request_count = self.env['item.requisition'].search_count(
                [('sale_order_id', '=', task.id)])

    def action_view_item_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_item_request').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        return action
    purchase_request_count = fields.Integer(
        string='Purchase Requests',
        compute='_compute_purchase_request_count'
    )
    

    def _compute_purchase_request_count(self):
        for task in self:
            task.purchase_request_count = self.env['po.requisition'].search_count(
                [('sale_order_id', '=', task.id)])

    def action_view_purchase_requests(self):
        """Return action to view cash requests related to the project."""
        action = self.env.ref(
            'psi_engineering.action_purchase_request').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        return action

    def action_confirm(self):
        """Confirm the sales order and link product specifications to the corresponding project."""
        super(SaleOrder, self).action_confirm()

        for order in self:

            project = self.env['project.project'].search(
                [('sale_order_id', '=', order.id)], limit=1)

            if project:
                specifications = self.env['product.specification'].search(
                    [('sale_id', '=', order.id)])
                for spec in specifications:
                    spec.project_specification_id = project.id
