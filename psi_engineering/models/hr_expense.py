from odoo import models, fields, api,_
from odoo.exceptions import UserError,ValidationError
import json

class HRExpense(models.Model):
    _inherit = "hr.expense"

    state = fields.Selection(
        [
            ('draft', 'To Submit'),
            ('submitted', 'Submitted'),
            ('md_approval', 'MD Approval'),
            ('approved', 'Approved'),
            ('post', 'Posted'),
            ('done', 'Done'),
            ('refused', 'Rejected'),
            ('reported', 'Reported')
        ],
        string="Status",
        index=True,
        required=True,
        default='draft',
        tracking=True,
        copy=False,
    )

    lead_id = fields.Many2one('crm.lead', string="Related Lead", readonly=True)
    project_id = fields.Many2one('project.project', string="Project",required=True)
    budget_id = fields.Many2one("budget.analytic", string="Budget", tracking=True)
    budget_line_id = fields.Many2one(
        'budget.line',
        string="Budget Line",
        domain="[('budget_analytic_id', '=', budget_id)]",
        required=True,
    )
    product_domain = fields.Char("Product Domain", compute="compute_product_domain", store=False)
    product_id = fields.Many2one('product.product', string='Product')
    remaining_amount = fields.Float("Remaining Amount")

    show_budget_warning = fields.Boolean("Show Budget Warning", compute="compute_show_budget_warning", store=True)

    @api.depends('total_amount', 'budget_line_id.remaining_amount')
    def compute_show_budget_warning(self):
        """
        Check if this individual expense line exceeds its budget line's remaining amount.
        """
        for rec in self:
            if rec.budget_line_id and rec.total_amount > rec.budget_line_id.remaining_amount:
                rec.show_budget_warning = True
            else:
                rec.show_budget_warning = False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Automatically set the budget based on the selected project."""
        if self.project_id:
            if self.project_id.budget_id:
                self.budget_id = self.project_id.budget_id.id
            else:
                self.budget_id = False

    
    @api.depends('budget_id', 'project_id')
    def compute_product_domain(self):
        """Compute domain for product_id based on budget lines."""
        for record in self:
            if record.budget_id:
                budget_lines = self.env['budget.line'].search([
                    ('budget_analytic_id', '=', record.budget_id.id),
                    ('product_id', '!=', False),
                    ('product_id.can_be_expensed', '=', True)
                ])
                product_ids = budget_lines.mapped('product_id').ids
                record.product_domain = "[('id', 'in', %s)]" % product_ids
            else:
                record.product_domain = "[]"

    def set_budget_line(self):
        """Set the budget line and remaining amount based on the selected product."""
        for line in self:
            if line.product_id and line.budget_id:
                budget_line = line.budget_id.budget_line_ids.filtered(
                    lambda x: x.product_id and x.product_id.id == line.product_id.id
                )
                if budget_line:
                    line.write({
                        'remaining_amount': budget_line[0].remaining_amount,
                        'budget_line_id': budget_line[0].id,
                    })

    @api.onchange('budget_id')
    def _onchange_budget_id(self):
        """Validate that the selected budget belongs to the selected project."""
        for rec in self:
            if rec.project_id and rec.budget_id:
                if not rec.project_id.budget_id:
                    raise UserError(_("The Project does not have a budget. Consider creating the budget first."))
                if rec.project_id.budget_id.id != rec.budget_id.id:
                    raise UserError(_("The selected budget does not belong to the selected project."))   
    @api.constrains('state')
    def _check_attachment(self):
        for record in self:
            if record.state == 'submitted':
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'hr.expense'),
                    ('res_id', '=', record.id)
                ])
                if not attachments:
                    raise ValidationError("You must attach a supporting document before submitting this expense.")
                

    custom_sequence = fields.Char(string='Expense Reference', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('custom_sequence'):
                vals['custom_sequence'] = self.env['ir.sequence'].next_by_code('hr.expense.custom.sequence')
        return super(HRExpense, self).create(vals_list)
    
    def btn_md_approval(self):
        for rec in self:
            rec.write({
                'state': 'approved',
            })

    def submit_md_approval(self):
        for rec in self:
            if not rec.budget_line_id:
                rec.set_budget_line()
            
            if not rec.budget_line_id or rec.total_amount > rec.budget_line_id.remaining_amount:
                rec.write({'state': 'md_approval'})
            else:
                rec.write({
                    'state': 'approved',
                })


