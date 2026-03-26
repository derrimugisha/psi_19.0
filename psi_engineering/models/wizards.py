from odoo import models, fields, api
from odoo.exceptions import UserError

class EstimationLeadWizard(models.TransientModel):
    _name = 'estimation.lead.wizard'
    _description = 'Estimation Lead Wizard'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    estimator_id = fields.Many2one('res.users', 
                                   string='Estimator', 
                                   required=True,
                                   domain=lambda self: [('id', 'in', self.env.ref('psi_engineering.group_estimator').users.ids)])
    estimation_due_date = fields.Date("Estiamtion Due Date")

    def assign_estimator(self):
        # Ensure the lead and estimator are provided
        if not self.lead_id or not self.estimator_id:
            raise UserError("Please select both Lead and Estimator.")

        # Assign the estimator to the lead's assigned_estimators field
        self.lead_id.write({'estimate_assignee_id': self.estimator_id.id,'sent_for_estimation':True})

        # Move the lead to the 'Estimation' stage
        estimation_stage = self.env['crm.stage'].search([('estimation_stage', '=', True)], limit=1)
        if estimation_stage:
            self.lead_id.stage_id = estimation_stage.id
            self.lead_id.estimation_due_date = self.estimation_due_date
            template = self.env.ref('psi_engineering.email_template_estimator_notification')
            if template:
                template.send_mail(self.lead_id.id, force_send=True)
        else:
            raise UserError("Estimation stage not found. Please create it in CRM Stages.")

        return {'type': 'ir.actions.act_window_close'}
    

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string="Analytic Account")

    wht_amount = fields.Monetary(
        string="WHT Amount",
        compute='_compute_wht_amount',
        
    )
    wht_tax_id = fields.Many2one(
        "account.tax", string="WHT Tax", default=lambda self: self.get_default_wht_tax())
    show_wht_amount = fields.Boolean("Show Wht Details", )
    actual_amount = fields.Monetary("Actual Amount", compute="_compute_wht_amount")
    # move_id = fields.Many2one("account.move", string="Bill/Receipt")
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True, readonly=True,
    )
    amount_tax = fields.Monetary(
        string='Tax',
        store=True, readonly=True,
    )
    
    withholding_amount_to_pay = fields.Monetary(
        string='WHT Amount To Pay',
        store=True, readonly=True,
        compute="_compute_wht_amount", 
    )

    @api.depends('amount_untaxed', 'amount_tax', 'amount','wht_tax_id',"payment_type","partner_id")
    def _compute_wht_amount(self):
        for rec in self:
            if rec.wht_tax_id:
                wht_tax = rec.wht_tax_id
            else:
                wht_tax = self.env['account.tax'].search(
                    [('type_tax_use', '=', 'purchase'),
                        ('is_wht', '=', True)],
                    limit=1
                )
                
            base_amount = rec.amount_untaxed
            total_wht_deductions = 0.0
            # total_vat_deductions = 0.0

            # Apply WHT deduction if 'apply_wht' is selected
            if wht_tax and wht_tax.amount > 0:
                wht_deduction = base_amount * (wht_tax.amount / 100.0)
                total_wht_deductions += wht_deduction
            
                # Calculate the final amount after deductions
                rec.withholding_amount_to_pay = total_wht_deductions
                rec.wht_amount = total_wht_deductions
                rec.actual_amount = rec.amount - total_wht_deductions
                
                # record.vat_amount_to_pay = total_vat_deductions
            else:
                rec.wht_amount = 0
                rec.actual_amount = rec.amount
    @api.model
    def get_default_wht_tax(self):
        wht_tax = self.env['account.tax'].search(
            [('type_tax_use', '=', 'purchase'), ('is_wht', '=', True)],
            limit=1
        )
        if wht_tax: 
            return wht_tax.id
        else:
            return False

    # @api.depends("wht_tax_id","amount","payment_type","partner_id")
    def _compute_wht_amount2(self):
        for rec in self:
            if rec.wht_tax_id:
                wht_tax = rec.wht_tax_id
            else:
                wht_tax = self.env['account.tax'].search(
                    [('type_tax_use', '=', 'purchase'),
                        ('is_wht', '=', True)],
                    limit=1
                )
            if wht_tax:
                rec.wht_amount = rec.amount * \
                    (wht_tax.amount / 100)
                rec.actual_amount = rec.amount - rec.wht_amount
            else:
                rec.wht_amount = 0
                rec.actual_amount = rec.amount


    def _create_payment_vals_from_wizard(self, batch_result):
        """ Override to pass analytic account to the payment """
        payment_vals = super(AccountPaymentRegister,
                             self)._create_payment_vals_from_wizard(batch_result)
        # Add the analytic account to the payment values

        if self.analytic_account_id:
            payment_vals['analytic_account_id'] = self.analytic_account_id.id

        self._compute_wht_amount()
        start_date = self.partner_id.wht_certificate_start_date
        end_date = self.partner_id.wht_certificate_end_date
        # if start_date and end_date and start_date >= self.payment_date and self.payment_date <= end_date and 
        if self.wht_tax_id and self.wht_amount > 0 and self.partner_id.wht_status == 'not_exempt' and self.payment_type == 'outbound':
            write_off_amount_currency = - self.wht_amount
            payment_vals['amount'] = self.actual_amount
            payment_vals['write_off_line_vals'].append({
                'name': "WHT TAX For %s ref %s" % (
                    self.partner_id.name, self.communication),
                'account_id': self.wht_tax_id.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': write_off_amount_currency,
                'balance': self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date),
            })

        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        res = super(AccountPaymentRegister,
                    self)._create_payment_vals_from_batch(batch_result)
        self._compute_wht_amount()
        start_date = self.partner_id.wht_certificate_start_date
        end_date = self.partner_id.wht_certificate_end_date
        # if start_date and end_date and start_date >= self.payment_date and self.payment_date <= end_date and 
        if (self.wht_tax_id and self.wht_amount > 0 and self.partner_id.wht_status == 'not_exempt' and self.payment_type == 'outbound') :
            write_off_amount_currency = - self.wht_amount
            res['amount'] = self.actual_amount
            res['write_off_line_vals'].append({
                'name': "WHT TAX For %s ref %s" % (
                    self.partner_id.name, self.communication),
                'account_id': self.wht_tax_id.account_id.id,
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'amount_currency': write_off_amount_currency,
                'balance': self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date),
            })
        if self.analytic_account_id:
            res['analytic_account_id'] = self.analytic_account_id.id

        return res
    
class PurchaseOrderRejectWizard(models.TransientModel):
    _name = 'purchase.order.reject.wizard'
    _description = 'Purchase Order Reject Wizard'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", required=True)
    reject_reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        """Set the rejection reason and update the status."""
        self.purchase_order_id.write({
            'reject_reason': self.reject_reason,
            'state': 'rejected',
        })

    

