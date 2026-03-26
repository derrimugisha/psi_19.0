from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime,timedelta
from markupsafe import Markup

import logging
_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = "account.asset"

    employee_id = fields.Many2one('hr.employee', string="Assigned Employee")

class AccountMove(models.Model):
    _inherit = 'account.move'

    project_id = fields.Many2one(
        'project.project', string="Project", tracking=True)
    partner_domain = fields.Char(
        "Partner Domain", compute="_compute_partner_domain", store=False)
    site_id = fields.Char( string="Site ID") 
    site_name = fields.Char(string="Site Name")
    
    accountability_status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed')
    ], string="Accountability status", default='pending' )

    is_recurring = fields.Boolean(
        string="Is Recurring",
        help="Indicates if this invoice is recurring.",
        copy=False
    )
    next_bill_date = fields.Date(
        string="Next Bill Date",
        help="Date for the next scheduled bill.",
        compute = "_compute_next_bill_date",
        store=True,
        copy=False
    )
    recurring_value = fields.Integer(
        string="Recurring Value",
        help="Enter a number to define the recurrence period (e.g., 2 for '2 weeks').",
        default=1,
        copy=False
    )
    recurring_unit = fields.Selection(
        [
            ('day', 'Day(s)'),
            ('week', 'Week(s)'),
            ('month', 'Month(s)'),
            ('year', 'Year(s)')
        ],
        string="Recurring Unit",
        help="Select the unit for the recurrence period.",
        default="month",
        copy=False
    )

    def compute_next_bill_date(self, base_date):
        """Computes the next bill date based on recurrence settings."""
        if not base_date:
            return False

        unit_mapping = {
            'day': timedelta(days=self.recurring_value),
            'week': timedelta(weeks=self.recurring_value),
            'month': relativedelta(months=self.recurring_value),
            'year': relativedelta(years=self.recurring_value)
        }

        return base_date + unit_mapping.get(self.recurring_unit, relativedelta(months=1))

    @api.depends('invoice_date', 'is_recurring', 'recurring_value', 'recurring_unit')
    def _compute_next_bill_date(self):
        """Computes the next bill date based on the user-defined recurring value and unit."""
        for rec in self:
            if rec.is_recurring and rec.invoice_date and rec.recurring_value > 0:
                if rec.recurring_unit == 'day':
                    delta = timedelta(days=rec.recurring_value)
                elif rec.recurring_unit == 'week':
                    delta = timedelta(weeks=rec.recurring_value)
                elif rec.recurring_unit == 'month':
                    delta = relativedelta(months=rec.recurring_value)
                elif rec.recurring_unit == 'year':
                    delta = relativedelta(years=rec.recurring_value)
                else:
                    delta = timedelta(days=30)

                rec.next_bill_date = rec.invoice_date + delta
            else:
                rec.next_bill_date = False   

    @api.model
    def duplicate_recurring_invoice(self):
        """Duplicates vendor bills that are recurring and updates the next bill date."""
        recurring_invoices = self.search([
            ('is_recurring', '=', True),
            ('next_bill_date', '<=', fields.Date.today())
        ])

        for invoice in recurring_invoices:
            invoice_copy = invoice.copy()

            # Set new invoice date to today
            invoice_copy.invoice_date = fields.Date.today()

            # Compute and set the next bill date for the copied invoice
            invoice_copy.next_bill_date = invoice_copy.compute_next_bill_date(invoice_copy.invoice_date)

            # Update the original invoice's next bill date
            invoice.next_bill_date = invoice.compute_next_bill_date(invoice.next_bill_date)

            # Post a message for tracking
            invoice_copy.message_post(body="This vendor bill has been duplicated as a recurring invoice.")

        return True

    def action_completed(self):
        for rec in self:
            rec.write({
                'accountability_status': 'completed',
            })
            

    def unlink(self):
        if not self.env.user.has_group('psi_engineering.group_md'):
            for record in self:
                if record.move_type in ['out_invoice', 'in_invoice']:
                    raise UserError("You cannot delete customer invoices or vendor bills.")
        return super(AccountMove, self).unlink()
    # purchase_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=False)

    # @api.onchange('purchase_id')
    # def  (self):
    #     """ Override to allow bill creation without a purchase order. """
    #     if not self.purchase_id:
    #         return

    def _get_finance_group_emails(self):
        finance_group_users = self.env.ref('psi_engineering.group_finance').users
        email_list = [user.email for user in finance_group_users if user.email]
        return ",".join(email_list) if email_list else ''

    def create_check_due_invoice_date(self):
        seven_days_ago = fields.Date.context_today(self) - timedelta(days=7)
        moves = self.env['account.move'].search([
            ('move_type', 'in', ['in_invoice', 'out_invoice']),
            ('invoice_date', '<=', seven_days_ago),
            ('availability_status', '=', 'pending'),
            ('payment_state', 'in', ['not_paid','partial']),
        ])
        for move in moves:            
            # Compose the notification message
            message = Markup(
                "<div>"
                "<p>Dear Invoice and Bill Due Team,</p>"
                "<p>An invoice with reference <strong><a href='%s'>%s</a></strong> is now overdue. "
                "Please review and proceed with approval at your earliest convenience.</p>"
                "<p>Thank you!</p>"
                "</div>"
            ) % (move.url, move.name)
            # Send the notification
            move.send_notification(message, [], subject="Invoice/Bill Overdue Notification")
            move.send_bill_invoice_email()

    def _send_weekly_finance_reminder(self):
        """Send a weekly reconciliation reminder email to the finance team every Monday."""
        template = self.env.ref('psi_engineering.finance_reconciliation_reminder_template')
        finance_team = self.env.ref('psi_engineering.group_finance').users

        for user in finance_team:
            if user.email:
                template.send_mail(self.id, force_send=True, email_values={'email_to': user.email})        
            
    def send_bill_invoice_email(self):
        template_id = self.env.ref(
            'psiengineering.invoice_bill_email_template').id
        self.env['mail.template'].browse(
            template_id).send_mail(self.id, force_send=True)
        self.message_post(body="The Bill/Invoice has been Sent")

    @api.onchange("move_type", "company_id")
    def _compute_partner_domain(self):
        for move in self:
            domain = []
            if move.company_id:
                domain.append(
                    ('company_id', 'in', (False, move.company_id.id)))
            if move.move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                # set domain for customer invoices
                domain.append(('is_customer', '=', True))
            elif move.move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                # set domain for vendor bills
                domain.append(('is_vendor', '=', True))
            move.partner_domain = str(domain)

    def set_analytic_distribution(self):
        """Set analytic distribution in the move lines if not set and the move has a project with an analytic account."""
        for move in self:
            if move.project_id and move.project_id.analytic_account_id:
                # Get the analytic account from the project
                analytic_account = move.project_id.analytic_account_id

                for line in move.line_ids:
                    # If the analytic distribution is not set, apply the analytic account
                    if not line.analytic_distribution:
                        # Set 100% distribution to the project analytic account
                        line.analytic_distribution = {
                            analytic_account.id: 100.0}

    def post(self):
        self.set_analytic_distribution()
        res = super().post()
        return res
    
    # @api.model
    # def create(self, vals):
    #     """Override the create method to add payment and reconciliation for bills."""
    #     move = super(AccountMove, self).create(vals)
    #     if move.move_type in ['in_receipt', 'in_invoice'] and move.requisition_id and move.requisition_id.employee_journal_id:  # Check if it's a vendor bill
    #         move._create_payment_and_reconcile()
    #     return move

    
    
    def _create_payment_and_reconcile(self):
        """Create payment and reconcile it with the bill."""
        for move in self:
            if move.state != 'posted':
                move.action_post()
            
            payment_vals = {
                'partner_id': move.partner_id.id,
                'amount': move.amount_total,
                'currency_id': move.currency_id.id,
                'payment_type': 'outbound',  # Outbound for vendor payment
                'journal_id': move.requisition_id.employee_journal_id.id,  # Default journal for payments
                'date': fields.Date.context_today(self),
                'memo': move.name,  # Reference to the bill
            }
            payment = self.env['account.payment'].create(payment_vals)
            payment._generate_journal_entry()
            payment.action_post()  
            payment.action_validate()

            # Reconcile the payment with the bill
            for line in payment.move_id.line_ids:
                if line.credit > 0:
                    move.js_assign_outstanding_line(line.id)
                    
    def action_register_payment(self):
        res = super(AccountMove, self).action_register_payment()
        amount_untaxed = sum(self.mapped('amount_untaxed'))
        amount_tax = sum(self.mapped('amount_tax'))
        
        res['context'].update({
            
            'default_amount_untaxed': amount_untaxed,
            'default_amount_tax': amount_tax,

        })
        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    project_id = fields.Many2one(
        'project.project', string="Project", tracking=True)
    cash_request_id = fields.Many2one(
        'cash.request', string="Cash Request", tracking=True)
    wht_move_id = fields.Many2one(
        'account.move',
        string="WHT Journal Entry",
        readonly=True,
        help="Journal entry for the WHT tax deduction."
    )

    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account", tracking=True)

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account_id(self):
        """ Set analytic distribution on journal items when analytic account is changed """
        if self.analytic_account_id:
            # Get all the journal items (account.move.line) related to this payment
            move_lines = self.move_id.line_ids
            # Define the analytic distribution (in this example, 100% for the selected analytic account)
            analytic_distribution = {self.analytic_account_id.id: 100.0}

            # Apply the analytic distribution to each journal item
            for line in move_lines:
                line.analytic_distribution = analytic_distribution

    # def _prepare_move_line_default_vals(self, write_off_line_vals=None):
    #     """Override to add analytic account to journal items during payment"""
    #     move_line_vals = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)
    #     # Apply the analytic account to all move lines generated by this payment
    #     for move_line in move_line_vals:
    #         if self.analytic_account_id:
    #             move_line['analytic_distribution'] = {self.analytic_account_id.id:100}

    #     return move_line_vals



class StockMove(models.Model):
    _inherit = 'stock.move'

    project_id = fields.Many2one(
        'project.project', string="Project", tracking=True)

    def _prepare_extra_move_vals(self, qty):
        vals = super(StockMove, self)._prepare_extra_move_vals(qty)
        if self.project_id:
            vals['project_id'] = self.project_id.id
        if self.purchase_line_id and self.purchase_line_id.order_id.project_id and not self.project_id:
            vals['project_id'] = self.purchase_line_id.order_id.project_id.id
        return vals

    def _prepare_move_split_vals(self, uom_qty):
        vals = super(StockMove, self)._prepare_move_split_vals(uom_qty)
        if self.project_id:
            vals['project_id'] = self.project_id.id
        if self.purchase_line_id and self.purchase_line_id.order_id.project_id and not self.project_id:
            vals['project_id'] = self.purchase_line_id.order_id.project_id.id
        return vals

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        result = super()._generate_valuation_lines_data(partner_id, qty, debit_value,
                                                        credit_value, debit_account_id, credit_account_id, svl_id, description)
        for key, value in result.items():
            if key == 'debit_line_vals':
                if self.project_id and self.project_id.account_id :
                    
                    value['analytic_distribution'] = {
                        self.project_id.account_id.id: 100}
                elif  self.location_id.project_id and self.location_id.project_id.account_id :
                    value['analytic_distribution'] = {
                        self.location_id.project_id.account_id.id: 100}
                elif self.location_dest_id.project_id and self.location_id.project_id.account_id:
                    value['analytic_distribution'] = {
                        self.project_id.location_dest_id.account_id.id: 100}
                    
        return result


class StockLocation(models.Model):
    _inherit = "stock.location"

    project_id = fields.Many2one("project.project", string="Project ")
    project_location = fields.Boolean("Is Project Location")    
    
    
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    STATUS = [
        ('draft', 'Draft'),
        # ('submitted', 'Project Manager Approval'),
        ('finance_add_funds', 'Finance Add Funds'),
        ('md_approval', 'MD Approval'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
    ]
    reject_reason = fields.Text(string="Rejection Reason")

    def action_reject(self):
        """Open a wizard to enter the rejection reason before rejecting the PO."""
        return {
            'name': 'Reject Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_order_id': self.id},
        }

    state = fields.Selection(STATUS, default='draft',
                             tracking=True, index=True)
    approval_date = fields.Datetime(string="Approval Date", tracking=True)

    project_id = fields.Many2one(
        'project.project', string="Project", tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Vendor',
        domain="[('is_vendor', '=', True), ('state', '=', 'approved')]",
        required=True
    )
    cash_request_id = fields.Many2one("cash.request", string="Transffer Request")
    task_id = fields.Many2one("project.task", string="Project Task ")
    project_manager_id = fields.Many2one(
        'res.users', string="Project Manager",
        readonly=True,
        domain=lambda self: [('id', 'in', self.env.ref('psi_engineering.group_project_manager').users.ids)]
        )
    budget_id = fields.Many2one("budget.analytic", string="Budget",tracking=True)

    @api.onchange('budget_id')
    def _onchange_budget_id(self):
        for rec in self:
            if rec.project_id and rec.budget_id:
                if not rec.project_id.budget_id:
                    raise UserError(_("The Project does not have a budget. Consider creating the budget first"))
                if rec.project_id.budget_id and rec.project_id.budget_id.id != rec.budget_id.id:
                    raise UserError(_("Please the budget selected does not belong to the project selected"))
    # remaining_amount = fields.Float("Remaining Amount")
    

    def _prepare_picking(self):
        res = super(PurchaseOrder,self)._prepare_picking()
        res.update({
            'user_id': self.user_id.id,
        })
        return res
      

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
                
                rec.state = 'finance_add_funds'
                rec.approval_date = datetime.now()
            else:
                rec.state = 'finance_add_funds'

    
    def request_transfer_money(self):
        for rec in self:
            
            if len(rec.order_line) == 0:
                raise UserError('Please first add the Items Before Requesting for Cash')
            lines = [(0,0,{'item':line.product_id.name,'product_id':line.product_id.id,'qty':line.product_qty,'unit_price':line.price_unit,'budget_line_id':line.budget_line_id.id if line.budget_line_id else False})for line in rec.order_line]
            
            return {
                'name':'Cash Request',
                'res_model':'cash.request',
                'view_mode':'form',
                'view_id':self.env.ref('psi_engineering.view_transfer_request_form').id,
                'type':'ir.actions.act_window',
                'target':'new',
                'context':{'default_amount_requested':rec.amount_total,'default_purchase_order_id':rec.id,'default_budget_id':rec.budget_id.id if rec.budget_id else False, 'default_project_id':rec.project_id.id if rec.project_id else False,'default_employee_id':self.env.user.employee_id.id,'default_cash_line_ids':lines}
            }
    # def project_approval(self):
    #     for rec in self:
    #         if rec.state != 'submitted':
    #             raise ValidationError(
    #                 "Purchase Order must be submitted first.")
    #         rec.state = 'project_approval'
    #         rec.approval_date = datetime.now()
    
    def view_cash_request(self):
        for rec in self:
            return {
                'name':rec.cash_request_id.name,
                'res_model':'cash.request',
                'res_id':rec.cash_request_id.id,
                'view_mode':'form',
                'target':'current',
                'type':'ir.actions.act_window',
                'view_id':self.env.ref('psi_engineering.view_transfer_request_form').id,
                'context':{
                    'create':False,
                    'delete':False,
                    # 'edit':False,
                }
            }

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
                    'state': 'finance_add_funds',
                    'approval_date': datetime.now()
                })
            else:
                raise ValidationError("Only the assigned project manager or MD can approve the funds.")

    def finance_add_funds(self):
        for rec in self:
            if rec.state != 'finance_add_funds':
                raise ValidationError("MD approval requires Finance to add funds first.")
            
            if rec.project_id:
                if not rec.budget_id:
                    raise ValidationError("The selected project has no budget associated. Please assign a budget before proceeding.")
                
                if rec.budget_id.state != 'confirmed':  # Replace 'confirmed' with your confirmed state
                    raise ValidationError("The budget associated with the project is not in the 'confirmed' state. Please confirm the budget before proceeding.")
            
            md_approval = False

            if rec.budget_id:
                for line in rec.order_line.filtered(lambda x: not x.budget_line_id):
                    line.set_budget_line()

                for line in rec.order_line:
                    if not line.budget_line_id:
                        md_approval = True
                    else:
                        remaining_amount = line.budget_line_id.remaining_amount
                        if line.price_subtotal > remaining_amount:
                            md_approval = True

                if md_approval:
                    rec.write({
                        'state': 'md_approval',
                        'approval_date': fields.Datetime.now(),
                    })
                else:
                    rec.order_line._validate_analytic_distribution()
                    rec._add_supplier_to_product()
                    rec.button_approve()
                    rec.approval_date = datetime.now()
            else:
                rec.write({
                    'state': 'md_approval',
                    'approval_date': fields.Datetime.now(),
                })
               

    def purchase_order(self):
        for rec in self:
            if rec.state != 'md_approval':
                raise ValidationError("Cannot make a purchase before MD approval.")
            
            if rec.project_id:
                if not rec.project_id.budget_id:
                    raise ValidationError("The selected project has no budget associated. Please assign a budget before making a purchase.")
                
                if rec.project_id.budget_id.state != 'confirmed':
                    raise ValidationError("The budget associated with the project is not in the 'confirmed' state. Please confirm the budget before making a purchase.")
            
            rec.order_line._validate_analytic_distribution()
            rec._add_supplier_to_product()
            rec.button_approve()
            rec.approval_date = datetime.now()

    def cancel_order(self):
        for rec in self:
            rec.state = 'cancel'

    def reject_order(self):
        """Open a wizard to enter the rejection reason before rejecting the PO."""
        return {
            'name': 'Reject Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_order_id': self.id},
        }        


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_vendor = fields.Boolean(string="Is Vendor", default=False)
    is_customer = fields.Boolean(string="Is Vendor", default=False)
    partner_type = fields.Selection(
        [('customer', 'Customer'), ('vendor', 'Vendor'), ('other', 'Other'),('both','Both Customer and Vendor')], string="Contact Type")
    contact_reference = fields.Char(
        string="Contact Reference", copy=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Approval Status", default='draft', tracking=True, index=True, copy=False)

    wht_status = fields.Selection([
        ('exempt', 'Exempt'),
        ('not_exempt', 'Not Exempt')
    ], string="WHT Status", default="not_exempt", tracking=True)

    wht_certificate_start_date = fields.Date(
        string="WHT Certificate Start Date")
    wht_certificate_end_date = fields.Date(string="WHT Certificate End Date")

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'res_partner_attachment_rel',
        'partner_id',
        'attachment_id',
        string="WHT Attachments",
        help="Upload related documents or certificates here."
    )
    
    id_attachment_ids = fields.Many2many(
        'ir.attachment',
        'res_partner_id_attachment_rel',
        'partner_id',
        'attachment_id',
        string="ID and Vendor Form",
        help="Upload related national ID here."
    )

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('psi_engineering.group_mgt'):
            raise UserError("You do not have permission to create new contacts. Only Management and Administrator can create contacts.")
        return super(ResPartner, self).create(vals)

    def action_submit_for_approval(self):
        self.write({'state': 'pending_approval'})

    def action_approve_vendor(self):
        if self.partner_type == 'vendor':
            ref = self.env['ir.sequence'].next_by_code('res.partner.vendor')
            self.write({'state': 'approved', 'is_vendor': True,
                       'supplier_rank': 1, 'contact_reference': f'V{ref[5:]}'})
        elif self.partner_type == 'customer':
            ref = self.env['ir.sequence'].next_by_code('res.partner.customer')
            self.write({'state': 'approved', 'is_customer': True,
                       'customer_rank': 1, 'contact_reference': f'C{ref[5:]}'})
        elif self.partner_type == 'both':
            ref_vendor = self.env['ir.sequence'].next_by_code('res.partner.vendor')
            self.write({
                'state': 'approved',
                'is_vendor': True, 
                'is_customer': True, 
                'supplier_rank': 1, 
                'customer_rank': 1,
                'contact_reference': f'CV{ref_vendor[5:]}',  
            })
        else:
            ref = self.env['ir.sequence'].next_by_code('res.partner.customer')
            self.write({'state': 'approved','is_vendor': False, 
                'is_customer': False, 
                'supplier_rank': 0, 
                'customer_rank': 0})        

    def action_draft_vendor(self):
        if self.partner_type == 'vendor':
            self.write(
                {'state': 'draft', 'is_vendor': False, 'supplier_rank': 0})
        elif self.partner_type == 'customer':
            self.write(
                {'state': 'draft', 'is_customer': False, 'customer_rank': 0})
        elif self.partner_type == 'both':
            self.write({
                'state': 'draft',
                'is_vendor': False, 
                'is_customer': False, 
                'supplier_rank': 0, 
                'customer_rank': 0, 
            })
        else:
            self.write({'state': 'draft','is_vendor': False, 
                'is_customer': False, 
                'supplier_rank': 0, 
                'customer_rank': 0}) 

    def action_reject_vendor(self):
        for rec in self:
            if self.partner_type == 'vendor':
                rec.write(
                    {'state': 'rejected', 'is_vendor': False, 'supplier_rank': 0})
            elif self.partner_type == 'customer':
                rec.write(
                    {'state': 'rejected', 'is_customer': False, 'customer_rank': 0})

            elif self.partner_type == 'both':
                self.write({
                    'state': 'rejected',
                    'is_vendor': False, 
                    'is_customer': False, 
                    'supplier_rank': 0, 
                    'customer_rank': 0, 
                })
            else:
                self.write({'state': 'rejected','is_vendor': False, 
                    'is_customer': False, 
                    'supplier_rank': 0, 
                    'customer_rank': 0})        

    def copy(self):
        raise UserError(
            _("Please you cannot duplicate a contact please create one "))

    @api.constrains('state')
    def _check_attachment(self):
        for record in self:
            if record.partner_type in ['vendor', 'both'] and record.state == 'pending_approval':
                if not record.id_attachment_ids:
                    raise ValidationError("You must attach a national ID for this vendor.")                


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_wht = fields.Boolean(string="Is WHT?", default=False)
    account_id = fields.Many2one("account.account", string="WHT Account")


class ClientType(models.Model):
    _name = "client.type"
    _description = "Client Type"

    name = fields.Char("Client Type")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    material_cost_ids = fields.Many2many(
        'material.costs', string="Material Costs")
    labour_cost_ids = fields.Many2many('labour.costs', string="Labour Costs")
    product_specification_ids = fields.Many2many(
        'product.specification', string="Product Specifications")
    overhead_costs_ids = fields.Many2many(
        'overhead.costs', string="Overhead Costs")
    equipment_cost_ids = fields.Many2many(
        'equipment.estimated.cost', string="Equipment Costs")
    total_material_cost = fields.Float(
        string="Total Material Cost", compute="_compute_total_costs")
    total_labour_cost = fields.Float(
        string="Total Labour Cost", compute="_compute_total_costs")
    total_specification_cost = fields.Float(
        string="Total Product Specification Cost", compute="_compute_total_costs")
    opportunity_id = fields.Many2one('crm.lead', string="Opportunity")
    site_id = fields.Char( string="Site ID") 
    site_name = fields.Char(string="Site Name")
    
    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a sale order,
        including custom fields: document, date_from, and date_to.
        """
        # Call the super method to get the original invoice values
        values = super(SaleOrder, self)._prepare_invoice()
        
        values.update({
            'site_id': self.site_id,
            'site_name': self.site_name,
        })

        return values                      
 

    @api.depends('material_cost_ids', 'labour_cost_ids', 'product_specification_ids')
    def _compute_total_costs(self):
        for order in self:
            order.total_material_cost = sum(
                cost.total_cost for cost in order.material_cost_ids)
            order.total_labour_cost = sum(
                cost.total_cost for cost in order.labour_cost_ids)
            order.total_specification_cost = sum(
                spec.price_subtotal for spec in order.product_specification_ids)

    def _create_sales_contract(self, project, sale_order):
        """ Create a sales contract for the created project """
        contract_vals = {
            'name': f"Sales Contract for {project.name}",
            'partner_id': sale_order.partner_id.id,
            'project_id': project.id,
            'sale_order_id': sale_order.id,
            'start_date': fields.Date.today(),
            # Example, set an end date 30 days later
            'end_date': fields.Date.add(fields.Date.today(), days=30),
            # Add additional contract details as necessary
        }

        # Create the sales contract
        self.env['sales.contract'].create(contract_vals)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        for order in self:
            for line in order.order_line:
                if line.project_id and line.product_specification_id:
                    # Create budget for the project
                    self._create_project_budget(
                        line.project_id, line.product_specification_id)

        return res



    def _create_project_budget(self, project, product_specification):

        """ Create a budget for the project based on the product specification """
        budget_vals = {
            'name': f"Budget for {project.name}",
            'project_id': project.id,
            'partner_id': self.partner_id.id,
            'product_specification': product_specification.id,
            'date_from': project.date_start or fields.Date.today(),
            'date_to': project.date_end or (fields.Date.today() + timedelta(days=90)),
            'budget_line_ids': []
        }

        # Step 1: Add Material Costs to the Budget
        for material_cost in product_specification.material_costs_ids:
            budget_line_vals = {
                'name': material_cost.description or 'Material Cost',
                'account_id': project.account_id.id,
                'product_id': material_cost.product_id.id,
                'project_id': project.id,
                'quantity': material_cost.quantity,
                'unit_price': material_cost.unit_price,
                'product_specification': product_specification.id,
                # 'budget_amount': -1 * material_cost.total_cost,
                # 'date_from': project.date_start,
                # 'date_to': project.date_end,
                'currency_id': self.currency_id.id,
                'description': material_cost.description or 'Material Cost',
            }
            budget_vals['budget_line_ids'].append(
                (0, 0, budget_line_vals))

        # Step 2: Add Labour Costs to the Budget
        for labour_cost in product_specification.labour_costs_ids:
            budget_line_vals = {
                # 'general_budget_id': expense_position,
                'name': labour_cost.name or 'Labour Cost',
                'project_id': project.id,
                'account_id': project.account_id.id,
                'product_id': labour_cost.product_id.id if labour_cost.product_id else False,
                # 'date_from': project.date_start,
                # 'date_to': project.date_end,
                # 'budget_amount': -1 * labour_cost.total_cost,
                'currency_id': self.currency_id.id,
                'product_specification': product_specification.id,
                'description': labour_cost.name or 'Labour Cost',
            }
            budget_vals['budget_line_ids'].append(
                (0, 0, budget_line_vals))

        # Step 3: Add Overhead Costs to the Budget
        for overhead_cost in product_specification.overhead_costs_ids:
            budget_line_vals = {
                # 'general_budget_id': expense_position,
                'name': overhead_cost.description or 'Overhead Cost',
                'account_id': project.account_id.id,
                'project_id': project.id,
                # 'date_from': project.date_start,
                # 'date_to': project.date_end,
                'currency_id': self.currency_id.id,
                # If overhead cost doesn't have a product_id
                'product_id': overhead_cost.product_id.id if overhead_cost.product_id else False,
                # 'budget_amount': -1 * overhead_cost.total_overhead_cost,
                'product_specification': product_specification.id,
                'description': overhead_cost.description or 'Overhead Cost',
            }
            budget_vals['budget_line_ids'].append(
                (0, 0, budget_line_vals))

        for equipment_cost in product_specification.equipment_cost_ids:
            budget_line_vals = {
                # 'general_budget_id': expense_position,
                'name': equipment_cost.description or 'Equipment Cost',
                'account_id': project.account_id.id,
                'project_id': project.id,
                # 'date_from': project.date_start,
                # 'date_to': project.date_end,
                'currency_id': self.currency_id.id,
                'quantity': equipment_cost.quantity,
                'unit_price': equipment_cost.unit_cost,
                # If overhead cost doesn't have a product_id
                'product_id': equipment_cost.product_id.id if equipment_cost.product_id else False,
                # 'budget_amount': -1 * equipment_cost.total_amount,
                'product_specification': product_specification.id,
                'description': equipment_cost.description or 'Overhead Cost',
            }
            budget_vals['budget_line_ids'].append(
                (0, 0, budget_line_vals))
        # for order_line in self.order_line:
        #     budget_line_vals = {
        #         'general_budget_id': income_position,
        #         'name': order_line.name,
        #         'account_id': project.account_id.id,
        #         'project_id': project.id,
        #         'date_from': project.date_start,
        #         'date_to': project.date_end,
        #         'currency_id': self.currency_id.id,
        #         'quantity': order_line.product_uom_qty,
        #         'unit_price': order_line.price_unit,
        #         # If overhead cost doesn't have a product_id
        #         'product_id': order_line.product_id.id if order_line.product_id else False,
        #         'budget_amount':  order_line.price_subtotal,
        #         'product_specification': order_line.product_specification_id.id if order_line.product_specification_id else False,
        #         'description': order_line.name,
        #     }
        #     budget_vals['crossovered_budget_line'].append(
        #         (0, 0, budget_line_vals))

        # Step 4: Create the Budget
        budget = self.env['budget.analytic'].create(budget_vals)
        project.write({
            'budget_id': budget.id,
        })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_specification_id = fields.Many2one(
        'product.specification', string="Product Specification")
    contract_id = fields.Many2one("sales.contract", string="Contract")

    def _timesheet_create_project_prepare_values(self):
        """Generate project values"""
        vals = super()._timesheet_create_project_prepare_values()
        vals['crm_lead_id'] = self.order_id.opportunity_id.id if self.order_id.opportunity_id else False
        vals['date_start'] = self.order_id.opportunity_id.date_start
        vals['date_end'] = self.order_id.opportunity_id.date_end

        vals['product_specification_id'] = self.product_specification_id.id if self.product_specification_id.id else False
        # _logger.info(f"Prepared project values: {vals}")
        if self.product_specification_id:
            vals['site_id'] = self.product_specification_id.site_id
            vals['site_name'] = self.product_specification_id.site_name
        return vals
    

    def _timesheet_create_project(self):
        project = super(SaleOrderLine, self)._timesheet_create_project()
        project._compute_site_name()
        if self.product_specification_id:
            for labour in self.product_specification_id.estimation_id.labour_costs_ids:
                labour.write({
                    'project_id': project.id,
                })
            for material in self.product_specification_id.estimation_id.material_costs_ids:
                material.write({
                    'project_id': project.id,
                })
            for overhead in self.product_specification_id.estimation_id.overhead_costs_ids:
                overhead.write({
                    'project_id': project.id,
                })

            for overhead in self.product_specification_id.estimation_id.equipment_cost_ids:
                overhead.write({
                    'project_id': project.id,
                })
        return project


class SalesContract(models.Model):
    _name = 'sales.contract'
    _description = 'Sales Contract'

    name = fields.Char(string="Contract Name", required=True)
    partner_id = fields.Many2one(
        'res.partner', string="Customer", required=True)
    company_id = fields.Many2one(
        'res.company', string="Company", default=lambda self: self.env.company.id)
    terms_and_conditions = fields.Html(string="Terms and Conditions")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    budget_id = fields.Many2one('budget.analytic', string="Budget")
    project_id = fields.Many2one('project.project', string="Project")
    lead_id = fields.Many2one('crm.lead', string="Lead")
    project_manager_id = fields.Many2one('res.users', string="Project Manager")
    signatory_ids = fields.Many2many('res.partner', string="Signatories")

    # Optional tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed')
    ], string="Status", default='draft', tracking=True)

    def action_activate_contract(self):
        self.write({'state': 'active'})

    def action_close_contract(self):
        self.write({'state': 'closed'})


class HrEmployeeBase(models.Model):
    _inherit = 'hr.employee'

    journal_id = fields.Many2one(
        'account.journal', string="Journal", domain="[('type','=','cash')]", )
    unreconciled_threshold = fields.Float(string="Unreconciled Threshold")
    amount_unreconciled = fields.Float(
        string="Amount Unreconciled", compute="_compute_journal_balances")
    amount_reconciled = fields.Float(
        string="Amount Reconciled", compute="_compute_journal_balances")
    balance = fields.Float(
        string="Balance", compute="_compute_journal_balances")

    @api.depends('journal_id')
    def _compute_journal_balances(self):
        """ Compute the balance, unreconciled amount, and reconciled amount in the journal """
        for employee in self:
            if employee.journal_id:
                journal = employee.journal_id

                # Compute the total balance in the journal
                employee.balance = sum(self.env['account.move.line'].search([
                    ('journal_id', '=', journal.id),
                    ('account_id.reconcile', '=', True),
                    ('move_id.state', '=', 'posted')
                ]).mapped('balance'))

                # Compute the unreconciled amount (sum of all unreconciled lines)
                employee.amount_unreconciled = sum(self.env['account.move.line'].search([
                    ('journal_id', '=', journal.id),
                    ('account_id.reconcile', '=', True),
                    ('move_id.state', '=', 'posted'),
                    ('full_reconcile_id', '=', False)
                ]).mapped('balance'))

                # Compute the reconciled amount (sum of all reconciled lines)
                employee.amount_reconciled = sum(self.env['account.move.line'].search([
                    ('journal_id', '=', journal.id),
                    ('account_id.reconcile', '=', True),
                    ('move_id.state', '=', 'posted'),
                    ('full_reconcile_id', '!=', False)
                ]).mapped('balance'))
            else:
                employee.balance = 0.0
                employee.amount_unreconciled = 0.0
                employee.amount_reconciled = 0.0


class Employee(models.Model):
    _inherit = 'hr.employee'
    location_ids = fields.Many2many(
        'stock.location',
        'employee_location_rel',
        'employee_id',
        'location_id',
        string="Attached Locations",
        domain=[('usage', '=', 'internal')]
    )

    def action_cash_requisition(self):
        view_id = self.env['ir.model.data'].sudo().check_object_reference(
            'requisitions', 'cash_requisition_form')[1]

        context = {
            'default_employee_id': self.id,
            'default_department_id':self.department_id.id if self.department_id else False,
            'default_employee_journal_id': self.journal_id.id if self.journal_id.id else False
        }
        return {
            'name': _("Create Cash Requisition"),
            'res_model': 'cash.request',
            'view_id': view_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': context,
            'type': 'ir.actions.act_window',
        }


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    
    
    journal_id = fields.Many2one(related='employee_id.journal_id', readonly=True)
    unreconciled_threshold = fields.Float(related='employee_id.unreconciled_threshold', readonly=True)
    amount_unreconciled = fields.Float(related='employee_id.amount_unreconciled', readonly=True)
    amount_reconciled = fields.Float(related='employee_id.amount_reconciled', readonly=True)
    balance = fields.Float(related='employee_id.balance', readonly=True)


    def action_cash_requisition(self):
        view_id = self.env['ir.model.data'].sudo().check_object_reference(
            'requisitions', 'cash_requisition_form')[1]

        context = {
            'default_employee_id': self.id,
            'default_employee_journal_id': self.journal_id.id if self.journal_id.id else False
        }
        return {
            'name': _("Create Cash Requisition"),
            'res_model': 'cash.request',
            'view_id': view_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': context,
            'type': 'ir.actions.act_window',
        }

# Custom Assembly Line Configuration in Product Profile


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    project_id = fields.Many2one(
        'project.project', string="Project", tracking=True)

    @api.model
    def create(self, vals):
        picking = super(StockPicking, self).create(vals)
        if picking.move_ids_without_package:
            self._add_assembly_lines(picking)
        return picking

    def _add_assembly_lines(self, picking):
        for move in picking.move_ids_without_package:
            product = move.product_id
            if product.product_tmpl_id.is_assembly_line:
                for line in product.product_tmpl_id.assembly_line_ids:
                    picking.move_lines.create({
                        'picking_id': picking.id,
                        'product_id': line.component_product_id.id,
                        'product_uom_qty': line.quantity * move.product_uom_qty,
                        'product_uom': line.product_uom_id.id,
                        'name': line.operation_description or product.display_name,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                    })

    # @api.depends('picking_type_id')
    # def _compute_allowed_locations(self):
    #     """ Computes allowed destination locations based on the logged-in user's attached locations. """
    #     for record in self:
    #         employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
    #         if employee:
    #             record.allowed_location_ids = employee.location_ids
    #         else:
    #             record.allowed_location_ids = False

    # allowed_location_ids = fields.Many2many(
    #     'stock.location',
    #     compute='_compute_allowed_locations',
    #     string="Allowed Locations"
    # )

    # location_dest_id = fields.Many2one(
    #     'stock.location',
    #     string="Destination Location",
    #     domain="[('id', 'in', allowed_location_ids)]"
    # )                


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Boolean field to check if product is an assembly line
    is_assembly_line = fields.Boolean(string='Is Assembly Line')

    # One2many field to link the custom assembly lines to product
    assembly_line_ids = fields.One2many(
        'product.assembly.line', 'product_tmpl_id', string='Custom Assembly Lines'
    )

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('psi_engineering.group_mgt'):
            raise UserError("You do not have permission to create new products. Only Management and Administrator can create products.")
        return super(ProductTemplate, self).create(vals)

    @api.constrains('is_assembly_line', 'assembly_line_ids')
    def _check_assembly_lines(self):
        for product in self:
            if product.is_assembly_line and not product.assembly_line_ids:
                raise ValidationError(
                    _('An assembly product must have at least one component product.'))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # One2many field to link the custom assembly lines to product
    assembly_line_ids = fields.One2many(
        'product.assembly.line', 'component_product_id', string='Custom Assembly Lines'
    )

    @api.model
    def create(self, vals):
        # Auto-generate internal reference if not provided
        if not vals.get('default_code'):
            sequence = self.env['ir.sequence'].next_by_code('product.product') or '/'
            vals['default_code'] = sequence
        return super(ProductProduct, self).create(vals)


class ProductAssemblyLine(models.Model):
    _name = 'product.assembly.line'
    _description = 'Product Assembly Line'

    # Reference to product template
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template', required=True, ondelete='cascade')

    # Component product for assembly
    component_product_id = fields.Many2one(
        'product.product', string='Component Product')

    # Quantity required for the component
    quantity = fields.Float(string='Quantity Required',
                            default=1.0, required=True)

    # Sequence of the assembly operation
    sequence = fields.Integer(string='Sequence', default=1)

    # Operation description
    operation_description = fields.Char(string='Operation Description')

    # Unit of Measure for the component
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure', required=True)

    product_id = fields.Many2one(
        "product.product", string="Component", required=True, domain=[('type', '=', 'product')])

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.component_product_id = self.product_tmpl_id.product_variant_id

    @api.onchange('component_product_id')
    def _onchange_component_product_id(self):
        if self.component_product_id:
            self.product_tmpl_id = self.component_product_id.product_tmpl_id

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        if self.component_product_id and self.product_uom_id:
            if self.product_uom_id.category_id != self.component_product_id.uom_id.category_id:
                raise UserError(
                    _('The selected Unit of Measure must be in the same category as the product.'))


class AccountAccount(models.Model):
    
    _inherit = "account.account"
    
    is_transfer_account = fields.Boolean('Is Transfer Account')

class BudgetReport(models.Model):
    _inherit = 'budget.report'
    
    def _get_pol_query(self, plan_fnames):
        return SQL(
            """
            SELECT (pol.id::TEXT || '-' || ROW_NUMBER() OVER (PARTITION BY pol.id ORDER BY pol.id)) AS id,
                
                bl.budget_analytic_id AS budget_analytic_id,
                bl.id AS budget_line_id,              -- Ensure this remains for backward compatibility
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
            JOIN purchase_order po ON pol.order_id = po.id AND po.state IN ('purchase', 'done')
        CROSS JOIN JSONB_TO_RECORDSET(pol.analytic_json) AS a(rate FLOAT, %(field_cast)s)
        LEFT JOIN budget_line bl 
                ON (pol.budget_line_id = bl.id 
                    OR (pol.product_id = bl.product_id 
                        AND po.company_id = bl.company_id 
                        AND po.date_order >= bl.date_from 
                        AND po.date_order <= bl.date_to))
        LEFT JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
            WHERE pol.qty_invoiced < pol.product_qty
            AND ba.budget_type != 'revenue'
            """,
            analytic_fields=SQL(', ').join(self.env['account.analytic.line']._field_to_sql('a', fname) for fname in plan_fnames),
            field_cast=SQL(', ').join(SQL(f'{fname} FLOAT') for fname in plan_fnames),
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
    # def _get_bl_query(self, plan_fnames):
    #     return SQL(
    #         """
    #         SELECT CONCAT('bl', bl.id::TEXT) AS id,
    #                bl.budget_analytic_id AS budget_analytic_id,
    #                bl.id AS budget_line_id,
    #                'budget.analytic' AS res_model,
    #                bl.budget_analytic_id AS res_id,
    #                bl.date_from AS date,
    #                ba.name AS description,
    #                bl.company_id AS company_id,
    #                NULL AS user_id,
    #                'budget' AS line_type,
    #                bl.budget_amount AS budget,
    #                0 AS committed,
    #                0 AS achieved,
    #                %(plan_fields)s
    #           FROM budget_line bl
    #           JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
    #         """,
    #         plan_fields=SQL(', ').join(self.env['budget.line']._field_to_sql('bl', fname) for fname in plan_fnames)
    #     )

