from odoo import fields, models, api, _
from datetime import date, time, datetime
import logging, json
from odoo.exceptions import ValidationError,UserError


_logger = logging.getLogger(__name__)
class ProjectCategory(models.Model):
    _name = 'project.category'
    _description = 'Project Category'

    name = fields.Char(string="Category Name", required=True)
    description = fields.Text(string="Description")
    no_quotation = fields.Boolean("No Quotation")
    project = fields.Boolean("Project")
class CrmStage(models.Model):
    _inherit ="crm.stage"
    
    estimation_stage = fields.Boolean('Is Estimation Stage')
    prequalified_stage = fields.Boolean('Is Prequalified')
    qualified_stage = fields.Boolean('Is Qualified')
    proposition_stage = fields.Boolean('Is Proposition Stage')
    progress_stage = fields.Boolean('Is Progress Stage')
    closed = fields.Boolean('Is Closed')
    is_new = fields.Boolean('Is New')
    submitted = fields.Boolean('Is Submitted')
    
    # @api.multi
    # @api.constrains("estimation_stage", )
    # def _check_estimation_stage(self):
    #     for stage in self:
    #         if stage.estimation_stage:
    #             stages = self.search([('estimation_stage','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one estimation stage')
    
    # @api.constrains("prequalified_stage",  )
    # def _check_prequalified_stage(self):
    #     for stage in self:
    #         if stage.prequalified_stage:
    #             stages = self.search([('prequalified_stage','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one Prequalified stage')
    
    # @api.constrains("qualified_stage",  )
    # def _check_qualified_stage(self):
    #     for stage in self:
    #         if stage.qualified_stage:
    #             stages = self.search([('qualified_stage','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one Qualified stage')
    
    # @api.constrains("proposition_stage",  )
    # def _check_proposition_stage(self):
    #     for stage in self:
    #         if stage.proposition_stage:
    #             stages = self.search([('proposition_stage','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one Proposotion stage')
    
    # @api.constrains("progress_stage",  )
    # def _check_progress_stage(self):
    #     for stage in self:
    #         if stage.progress_stage:
    #             stages = self.search([('progress_stage','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one Progress stage')
    
    # @api.constrains("closed",  )
    # def _check_closed_stage(self):
    #     for stage in self:
    #         if stage.closed:
    #             stages = self.search([('closed','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one closed stage')
                
    # @api.constrains("is_won",  )
    # def _check_is_won_stage(self):
    #     for stage in self:
    #         if stage.is_won:
    #             stages = self.search([('is_won','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one won stage')
    
    
    # @api.constrains("submitted",  )
    # def _check_submitted_stage(self):
    #     for stage in self:
    #         if stage.submitted:
    #             stages = self.search([('submitted','=',True)])
    #             if len(stages) > 1:
    #                 raise UserError('Please there can only be one submitted stage')


class CrmLeadChecklist(models.Model):
    _name = 'crm.lead.checklist'
    _description = 'CRM Lead Checklist'

    name = fields.Char(string="Checklist Item", required=True)
    lead_id = fields.Many2one('crm.lead', string="Opportunity", ondelete='cascade')
    is_checked = fields.Boolean(string="Checked Off", default=False)
    percentage = fields.Float(string="Percentage", digits=(16,4), required=True, help="Contribution of this item to the checklist completion in %.")
    checklist_link = fields.Char("Document Link")

    @api.constrains('percentage')
    def _check_percentage_total(self):
        """Ensure that the total checklist percentage does not exceed 100% for each lead."""
        for record in self:
            total_percentage = sum(record.lead_id.checklist_ids.mapped('percentage'))
            if total_percentage > 100:
                raise ValidationError("Total percentage of checklist items cannot exceed 100%.")

    # @api.onchange('is_checked')
    def _onchange_is_checked(self):
        """Log a message to the CRM lead chatter when an item is checked off."""
        if self.is_checked and self.lead_id:
            self.lead_id.message_post(
                body=f"The checklist item '{self.name}' has been checked off by {self.env.user.name}.",
                # message_type="notification",
                # subtype_xmlid="mail.mt_note"
            )
class CrmLead(models.Model):
    
    _inherit = "crm.lead"
    
    estimation_due_date = fields.Date("Estiamtion Due Date")
    project_category_id = fields.Many2one('project.category', string="Project Category" ,copy=True)
    no_quotation = fields.Boolean("No Quotation Required", related="project_category_id.no_quotation", store=True)
    project = fields.Boolean("Project ", related="project_category_id.project", store=True)
    estimation_stage = fields.Boolean('Is Estimation Stage', related="stage_id.estimation_stage", store=True)
    prequalified_stage = fields.Boolean('Is Prequalified', related="stage_id.prequalified_stage", store=True)
    qualified_stage = fields.Boolean('Is Qualified', related="stage_id.qualified_stage", store=True)
    proposition_stage = fields.Boolean('Is Proposition Stage', related="stage_id.proposition_stage", store=True)
    progress_stage = fields.Boolean('Is Progress Stage', related="stage_id.progress_stage", store=True)
    closed = fields.Boolean('Is Closed', related="stage_id.closed", store=True)
    is_won = fields.Boolean('Is Won', related="stage_id.is_won", store=True)
    is_new = fields.Boolean('Is New', related="stage_id.is_new",store=True)
    date_start = fields.Date("Expected Start")
    date_end = fields.Date("Expected End")
    is_bid_boq = fields.Boolean("Required Bill Of Quantity")
    skip_sale_order = fields.Boolean(string="Skip Sales Order")
    
    estimate_assignee_id = fields.Many2one('res.users', string='Estimate Assignee', required=False,copy=True)
    is_readonly_estimate = fields.Boolean(string="Estimation Complete", help="Check this box to make the estimate fields read-only.")
    boq_line_ids = fields.One2many('bill.quantity', 'lead_id' , string="Bill Of Quantity",copy=True)
    product_specification_ids = fields.One2many('product.specification', 'lead_id' , string="Product Specification",copy=True)
    material_costs_ids = fields.One2many('material.costs', 'lead_id' , string="Material Costs",copy=True)
    labour_costs_ids = fields.One2many('labour.costs', 'lead_id' , string="Labour Costs",copy=True)
    overhead_costs_ids = fields.One2many('overhead.costs', 'lead_id' , string="Overhead Costs",copy=True)
    estimated_costs_ids = fields.One2many('estimated.costs', 'lead_id', string="Estimated Costs",copy=True)    
    amount_total_product_specification = fields.Monetary(string='Total', 
                                                   compute='_amount_total_product_specification', tracking=True, store=True)
    amount_total_material_costs = fields.Monetary(string='Total Material Costs', readonly=True, compute='_amount_total_material_costs', tracking=4)
    amount_total_labour_costs = fields.Monetary(string='Total Labour Costs', readonly=True, compute='_amount_total_labour_costs', tracking=4)
    amount_total_overhead_costs = fields.Monetary(string='Total Overhead Costs', readonly=True, compute='_amount_total_overhead_costs', tracking=4)
    amount_total_estimation_cost = fields.Monetary(string='Total Estimated Costs', readonly=True, compute='_compute_total_estimation_cost', tracking=4)
    amount_total = fields.Monetary(string='Total', readonly=True,
                                                   compute='_amount_total_all', tracking=4)
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id.id, tracking=True,copy=True)
    
    amount_total = fields.Monetary(string='Total Sales', readonly=True, compute='_compute_amount_total', tracking=4)
    site_survey_received = fields.Boolean("Site Survey Received")
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',copy=True)
    project_count = fields.Integer(string="Project", compute="_compute_project_count")
    cost_total = fields.Monetary(string='Total Cost', readonly=True, compute='_compute_cost_total', tracking=4)
    margin_price_total = fields.Monetary(string='Total Cost With Margin', readonly=True, compute='_compute_margin_total', tracking=4)
    task_overhead_id = fields.One2many('task.overhead', 'crm_lead_id',string='Task Overhead',copy=True)
    # overhead_costs_ids = fields.One2many('overhead.costs', 'task_id', string="Overhead Costs")
    task_material_id = fields.One2many('task.material','crm_lead_id',string='Task Material',copy=True)
    task_labour_id = fields.One2many('task.labour','crm_lead_id',string='Task Labour')
    task_estimatecost_id = fields.One2many('task.estimatedcosts','crm_lead_id',string='Task Estimate Cost',copy=True)
    require_bid = fields.Boolean(string="Require Bid?")
    # bid_ids = fields.One2many('bid', 'lead_id', string="Bids")
    # bid_count = fields.Integer(string="Bid Count", compute='_compute_bid_count')
    expense_ids = fields.One2many('hr.expense', 'lead_id', string="Expenses")
    total_expense_amount = fields.Monetary(string="Total Expense Amount", compute="_compute_total_expense_amount", store=True)
    serial_number = fields.Char(string="Serial Number")
    site_id = fields.Char( string="Site ID") 
    site_name = fields.Char(string="Site Name")
    show_product_specifications = fields.Boolean(string="Show Product Specifations", default=False, compute="_onchange_stage_id2")
    
    checklist_ids = fields.One2many('crm.lead.checklist', 'lead_id', string="Checklist",copy=True)
    checklist_completion = fields.Float(string="Checklist Completion (%)", compute='_compute_checklist_completion', store=True)

    @api.depends('checklist_ids.is_checked', 'checklist_ids.percentage')
    def _compute_checklist_completion(self):
        for lead in self:
            completion = sum(item.percentage for item in lead.checklist_ids if item.is_checked)
            lead.checklist_completion = completion
    
    client_type = fields.Many2one("client.type", string="Client Type",copy=True)
    equipment_cost_ids = fields.One2many('equipment.estimated.cost', 'lead_id', string='Equipment Estimated Costs',copy=True)

    # Total estimated cost (computed)
    total_equipment_estimated_cost = fields.Float(string='Total Estimated Cost', compute='_compute_total_estimated_cost', store=True)
    @api.depends('equipment_cost_ids.total_amount')
    def _compute_total_estimated_cost(self):
        for record in self:
            record.total_equipment_estimated_cost = sum(cost.total_amount for cost in record.equipment_cost_ids)
        
    @api.onchange('checklist_ids.is_checked','checklist_ids')
    def _onchange_is_checked(self):
        """Log a message to the CRM lead chatter when an item is checked off."""
        for rec in self:
            if len(rec.checklist_ids)>0:
                for line in rec.checklist_ids:
                    line.percentage = 100/len(rec.checklist_ids)
                    # if line.is_checked and line.lead_id:
                    #     rec.message_post(
                    #         body=f"The checklist item '{line.name}' has been checked off by {self.env.user.name}."
                            
                    #     )
    can_see_button = fields.Boolean(compute='_compute_can_see_button')

    def _compute_can_see_button(self):
        for record in self:
            record.can_see_button = (
                self.env.user.id == record.user_id.id or
                record.estimation_stage == False or
                self.env.user.has_group('psi_engineering.group_md')
            )
    @api.onchange("stage_id")
    def _onchange_stage_id2(self):
        for rec in self:
            if rec.stage_id.is_new or rec.stage_id.prequalified_stage:
                rec.show_product_specifications = False
            else:
                rec.show_product_specifications = True
                if not rec.stage_id.is_won:
                    rec.is_readonly_estimate = True
                
    # @api.depends('labour_costs_ids.total_cost', 'amount_total_material_costs', 'amount_total_overhead_costs','total_equipment_estimated_cost')
    # def _compute_total_estimation_cost(self):
    #     """Compute total estimated cost from material, labour, and overhead costs."""
    #     for task in self:
    #         task.amount_total_estimation_cost = task.amount_total_material_costs + task.amount_total_labour_costs + task.amount_total_overhead_costs +task.total_equipment_estimated_cost

    project_ids = fields.Many2many('project.project', string="Related Projects")
    def _compute_project_count(self):
        obj = self.env['project.project']
        for rec in self:
            rec.project_count = obj.search_count([('crm_lead_id', '=', rec.id)])
            
            
    def open_estimation_wizard(self):
        # Return an action that opens the wizard form view with the current lead set as the default
        if not self.product_specification_ids:
            raise models.UserError(_("Please first add some product specification for this leade"))
        return {
            'name':_("Assign Estimator"),
            'type': 'ir.actions.act_window',
            'res_model': 'estimation.lead.wizard',
            'view_id':self.env.ref("psi_engineering.view_estimation_lead_wizard_form").id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            }
        }
    
    def open_project(self):
        return {
            'name': _('Project Records'),
            'domain': [('crm_lead_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'project.project',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            } 
       
    # @api.model 
    # def write(self, values):
    #     res = super().write(values)
    #     for rec in self:
    #         rec._amount_total_product_specification()
    #         rec._onchange_amount_total_product_specification()
    #     return res
    
    def action_view_checklist_items(self):
        """Return action to open checklist items for the current CRM lead."""
        self.ensure_one()  # Ensures we're operating on a single record
        return {
            'name': 'Checklist Items',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead.checklist',
            'view_mode': 'list,form',
            'context': {'default_lead_id': self.id},
            'domain': [('lead_id', '=', self.id)],
            'target': 'current',
        }

    @api.depends('boq_line_ids.price_subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(line.price_subtotal for line in rec.boq_line_ids)
            
    @api.onchange("amount_total_product_specification")
    def _onchange_amount_total_product_specification(self):
        for rec in self:
            rec.expected_revenue = rec.amount_total_product_specification
    
    @api.depends('product_specification_ids.total_estimated_cost_withmargin','product_specification_ids')
    def _amount_total_product_specification(self):
        for rec in self:
            rec.amount_total_product_specification = sum(line.total_estimated_cost_withmargin for line in rec.product_specification_ids) 
            rec._onchange_amount_total_product_specification()

    @api.depends('material_costs_ids.total_cost')
    def _amount_total_material_costs(self):
        for lead in self:
            lead.amount_total_material_costs = sum(line.total_cost for line in lead.material_costs_ids)

    @api.depends('labour_costs_ids.total_cost')
    def _amount_total_labour_costs(self):
        for lead in self:
            lead.amount_total_labour_costs = sum(line.total_cost for line in lead.labour_costs_ids)

    @api.depends('overhead_costs_ids.total_overhead_cost')
    def _amount_total_overhead_costs(self):
        for lead in self:
            lead.amount_total_overhead_costs = sum(line.total_overhead_cost for line in lead.overhead_costs_ids)

    @api.depends('labour_costs_ids.total_cost', 'amount_total_material_costs', 'amount_total_overhead_costs', 'estimated_costs_ids.total_cost', 'expense_ids.total_amount_currency')
    def _compute_total_estimation_cost(self):
        """Compute total estimated cost from material, labour, overhead costs, estimated costs, and requisition amounts."""
        for lead in self:
            total_material_costs = sum(line.total_cost for line in lead.material_costs_ids)
            total_labour_costs = sum(line.total_cost for line in lead.labour_costs_ids)
            total_overhead_costs = sum(line.total_overhead_cost for line in lead.overhead_costs_ids)
            total_estimated_costs = sum(line.total_cost for line in lead.estimated_costs_ids)
            total_expense_amount = sum(line.total_amount_currency for line in lead.expense_ids)

            lead.amount_total_estimation_cost = total_material_costs + total_labour_costs + total_overhead_costs + total_estimated_costs + total_expense_amount + lead.total_equipment_estimated_cost


    @api.onchange('is_readonly_estimate')
    def _onchange_readonly_estimate(self):
        if self.is_readonly_estimate:
            # If the checkbox is checked, make the fields read-only.
            return {'readonly': {'product_specification_ids': True,
                                 'material_costs_ids': True,
                                 'labour_costs_ids': True,
                                 'overhead_costs_ids': True,
                                 'estimated_costs_ids': True}}
        else:
            # If unchecked, make fields editable.
            return {'readonly': {'product_specification_ids': False,
                                 'material_costs_ids': False,
                                 'labour_costs_ids': False,
                                 'overhead_costs_ids': False,
                                 'estimated_costs_ids': False}}
    
    @api.depends('boq_line_ids.cost')
    def _compute_cost_total(self):
        for rec in self:
            rec.cost_total = sum(line.cost_subtotal for line in rec.boq_line_ids)
    
    @api.depends('boq_line_ids.margin_price')
    def _compute_margin_total(self):
        for rec in self:
            rec.margin_price_total = sum(line.margin_price for line in rec.boq_line_ids)
            
    def action_qualified_stage(self):
        for rec in self:
            stage = self.env['crm.stage'].search([('qualified_stage','=',True)],limit=1)
            if stage:
                rec.write({
                    'stage_id': stage.id,
                })
                rec._onchange_stage_id2()
            else:
                raise UserError('Please the is no qualified Stage')

   
    def create_quotation(self):
        for rec in self:
            # if not rec.stage_id.is_won:
            #     raise UserError('Please the Lead/Opportunity must first be won inorder to create a Quotation')
            # if not rec.date_start or not rec.date_end:
            #     raise UserError(_("Please first fill the expected start date or end date"))
            if not rec.product_specification_ids:
                raise UserError('Please first add some Product Specifications before creating a Lead')
            order_lines = [] 
            for prod_sp in rec.product_specification_ids:
                if prod_sp.state not in ['approved']:
                    raise UserError(_("Please the Estimation for this specification %s must be approved first inorder to continue"%prod_sp.estimation_id.name))
                if prod_sp.total_estimated_cost_withmargin <= 0:
                    raise UserError('Please first add the estimates for this specification Line %s'%prod_sp.description)
                # if prod_sp.estimation_id.margin_value <= 0:
                #     raise UserError('Please first add the estimates margin for this specification Line %s'%prod_sp.description)
                if not prod_sp.site_id or not prod_sp.site_name:
                    raise UserError(_("Please first Set the Site ID or Site Name for this Specification "))
                line_values = {
                    'product_specification_id': prod_sp.id,
                    'product_id': prod_sp.product_id.id,
                    'name': prod_sp.description,
                    'product_uom_qty': prod_sp.quantity,
                    'product_uom': prod_sp.uom_id.id,
                    'price_unit': prod_sp.total_estimated_cost_withmargin / prod_sp.quantity if prod_sp.quantity > 0 else prod_sp.total_estimated_cost_withmargin, 
                }    
                # Append each line to the order_lines list
                order_lines.append((0, 0, line_values))
            
            # Prepare the quotation (sale order) values
            quotation_val = {
                'opportunity_id': rec.id,
                'origin': rec.name,
                'partner_id': rec.partner_id.id,
                'user_id': rec.user_id.id,
                'team_id': rec.team_id.id,
                'order_line': order_lines,
                'material_cost_ids':[(4, mat.id) for mat in rec.material_costs_ids],
                'product_specification_ids':[(4, mat.id) for mat in rec.product_specification_ids],
                'labour_cost_ids':[(4, mat.id) for mat in rec.labour_costs_ids],
                'overhead_costs_ids':[(4, mat.id) for mat in rec.overhead_costs_ids],
                'equipment_cost_ids':[(4, mat.id) for mat in rec.equipment_cost_ids],
                'site_id': rec.product_specification_ids[0].site_id,
                'site_name': rec.product_specification_ids[0].site_name,
                # Add all BOQ lines to the quotation
            }
            
            # Create the quotation (sale order)
            res = self.env['sale.order'].create(quotation_val)
            
            return rec.action_view_sale_quotation()
            
            

    sent_for_estimation = fields.Boolean("Sent For Estimation")
    
    def send_estimation(self):
        for rec in self:
            if not rec.product_specification_ids:
                raise UserError(_("Please first add some product specification for this leade"))
            stage = self.env['crm.stage'].search([('estimation_stage','=',True)],limit=1)
            if stage:
                rec.stage = stage.id
                rec.sent_for_estimation = True
            else:
                raise UserError('The Estimation Stage is not Set in the Systme. Kindly check with the Administrator')
            

        # create bid
    # def _create_bid(self):
    #     for lead in self:
    #         if not lead.bid_ids:
    #             try:
    #                 bid_vals = {
    #                     'lead_id': lead.id,
    #                     'source_id': lead.source_id.id if lead.source_id else False,
    #                     'partner_id': lead.partner_id.id if lead.partner_id else False,
    #                     'account_manager': lead.user_id.id if lead.user_id else False,
    #                     'description': lead.name,
    #                 }
    #                 bid = self.env['bid'].create(bid_vals)
    #                 self.env.cr.commit()
    #                 _logger.info(f"Bid created automatically for lead {lead.id}")
    #             except Exception as e:
    #                 self.env.cr.rollback()
    #                 _logger.error(f"Error creating bid for lead {lead.id}: {str(e)}")
    #                 raise  

    # def action_view_bids(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Bids',
    #         'res_model': 'bid',
    #         'view_mode': 'list,form',
    #         'domain': [('lead_id', '=', self.id)],
    #         'context': {'default_lead_id': self.id},
    #         'target': 'current',
    #     } 

    # @api.depends('bid_ids')
    # def _compute_bid_count(self):
    #     for lead in self:
    #         lead.bid_count = len(lead.bid_ids)

    # def write(self, vals):
    #     # Check if the stage is being changed to "Qualified"
    #     if 'stage_id' in vals:
    #         new_stage = self.env['crm.stage'].browse(vals['stage_id'])
    #         if new_stage.name == 'Qualified':
    #             self._create_bid()
    #     return super(CrmLead, self).write(vals) 

    expense_count = fields.Integer("Expense Count", compute="compute_expense_count")
    
    def action_view_expenses(self):
        for rec in self:
            return {
                'name':"Expenses",
                'res_model': "hr.expense",
                'view_mode':'list,form',
                'domain':[('lead_id','=',rec.id)],
                'type':'ir.actions.act_window',
                'context':{'default_lead_id':rec.id},
                'target':'current',
            }
            
    
    def compute_expense_count(self):
        for rec in self:
            rec.expense_count = self.env['hr.expense'].search_count([('lead_id','=',rec.id)])
    
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
                    'default_lead_id': record.id
                },
            }

    @api.depends('expense_ids.total_amount_currency')
    def _compute_total_expense_amount(self):
        for lead in self:
            lead.total_expense_amount = sum(lead.expense_ids.mapped('total_amount_currency'))
        

    def action_view_expenses(self):
        self.ensure_one()
        return {
            'name': 'Expenses',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],  
            'context': {'default_lead_id': self.id},
        }
                
    
class BillOfQuantity(models.Model):
    _name = 'bill.quantity'
    _description = 'Lines Bill Of Quantity'
    lead_id = fields.Many2one('crm.lead', string="Lead")
    milestone_id = fields.Many2one('milestone.milestone', string="Milestone")
    product_id = fields.Many2one('product.product', string="Item")
    name = fields.Text('Description')
    quantity = fields.Float(string='Quantity', default='1.00')
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=False, string='UOM')
    # cost = fields.Float(related="product_id.standard_price", readonly=False, string="Unit Cost")
    cost = fields.Float(readonly=False, string="Unit Cost")
    price_unit = fields.Float(related="product_id.list_price", readonly=False, string="Sale Price")
    price_subtotal = fields.Float(compute='_compute_subtotal', string='Subtotal', readonly=True, store=True)
    percentage = fields.Float(string='Margin Percentage%', default=0.00)
    margin_price = fields.Float(string='Unit Cost With Margin', compute='_margin_price')
    cost_subtotal = fields.Float(compute='_compute_cost_subtotal', string='Cost Subtotal', readonly=True, store=True)

    @api.depends('percentage','cost','quantity')
    def _margin_price(self):
        percent = 0.00
        amount = 0.00
        for line in self:
            if line.percentage > 0.00:
                percent = (line.cost * line.percentage / 100.00)
                subtotal = line.cost * line.quantity
                amount = subtotal + percent
            line.margin_price = amount
            
    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            subtotal = rec.price_unit * rec.quantity
            rec.update({
                'price_subtotal': subtotal,
            }) 
    @api.depends('quantity', 'cost')
    def _compute_cost_subtotal(self):
        for rec in self:
            subtotal = rec.cost * rec.quantity
            rec.update({
                'cost_subtotal': subtotal,
            }) 
            

class ProjectProject(models.Model):
    
    _inherit = "project.project"
    
    
    # product_specification_ids = fields.One2many('product.specification', 'project_id' , string="Product Specification")
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")
    cash_requests = fields.One2many(
        "cash.request", "project_id", string="Cash Requests")
    cash_request_lines = fields.One2many(
        "cash.request.lines", "project_id", string="Cash Request Lines")
    cash_request_amount = fields.Monetary(
        "Total Cash Request", currency_field="currency_id", compute="_compute_cash_request", store=True)
    item_requests = fields.One2many(
        "item.requisition", "project_id", string="Item Requests")
    item_request_lines = fields.One2many(
        "item.requisition.order.line", "project_id", string="Item Request Lines")
    
    purchase_orders = fields.One2many(
        "purchase.order", "project_id", string="Purchase Orders")
    purchase_orders_lines = fields.One2many(
        "purchase.order", "project_id", string="Purchase Order Lines")
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    purchase_total_amount = fields.Monetary(
        "Total Purchases", currency_field="currency_id", compute="_compute_total_purchases")
    
    total_actual_cost = fields.Monetary(
        "Total Actual Cost", currency_field="currency_id", compute="_compute_total_actual_cost")
    
    item_requests_count = fields.Integer(string="Material Internal Pickups", compute="_compute_item_requests")
    cash_requests_count = fields.Integer(string="Cash Request Count", compute="_compute_cash_requests")
    purchase_count = fields.Integer(string="Purchase Count", compute="_compute_purchase")
    sale_orders = fields.One2many(
        "sale.order", "project_id", string="Sales Orders")
    sale_total_amount = fields.Monetary(
        "Total Sales", currency_field="currency_id", compute="_compute_total_sales")
    
    invoice_total_amount = fields.Monetary(
        "Total Invoice", currency_field="currency_id", compute="_compute_total_invoice")
    
    total_balance = fields.Monetary(
        "Total Balance", currency_field="currency_id", compute="_compute_total_balance")
    purchase_requests_count = fields.Integer(string="Purchase Request Count", compute="_compute_purchase_requests")
    invoice_count = fields.Integer(string="Invoice Count", compute="_compute_invoice_count")
    equipment_cost_ids = fields.One2many('equipment.estimated.cost', 'project_id', string='Equipment Estimated Costs')

    # Total estimated cost (computed)
    total_equipment_estimated_cost = fields.Float(string='Total Estimated Cost', compute='_compute_total_estimated_cost', store=True)
    @api.depends('equipment_cost_ids.total_amount')
    def _compute_total_estimated_cost(self):
        for record in self:
            record.total_equipment_estimated_cost = sum(cost.total_amount for cost in record.equipment_cost_ids)
    def _compute_invoice_count(self):
        obj = self.env['account.move']
        for rec in self:
            rec.invoice_count = obj.search_count([('project_id', '=', rec.id)])
    
    def open_invoice(self):
        return {
            'name': _('Invoice Records'),
            'domain': [('project_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            } 
        
    def create_invoice(self):
        for rec in self:
            move_lines = []  
            for prod_sp in rec.product_specification_ids:
                product_account = prod_sp.product_id.property_account_income_id or prod_sp.product_id.categ_id.property_account_income_categ_id
                line_values = {
                    'product_id': prod_sp.product_id.id,
                    'name': prod_sp.product_id.name,
                    'quantity': prod_sp.quantity,
                    'product_uom_id': prod_sp.uom_id.id,
                    'price_unit': prod_sp.price_unit, 
                    'account_id': product_account.id,
                }    
                move_lines.append((0, 0, line_values))
            invoice_val = {
                'partner_id': rec.partner_id.id,
                'user_id': rec.user_id.id,
                'project_id': rec.id,
                'move_type': 'out_invoice',
                'invoice_line_ids': move_lines  
            }
            self.env['account.move'].create(invoice_val)

            
    @api.depends("sale_total_amount", "total_actual_cost")
    def _compute_total_balance(self):
        for rec in self:
            total = rec.sale_total_amount - rec.total_actual_cost
            rec.total_balance = total
            
    def _compute_item_requests(self):
        obj = self.env['item.requisition']
        for rec in self:
            rec.item_requests_count = obj.search_count([('project_id', '=', rec.id)])
    
    def open_item_requisition(self):
        return {
            'name': _('Material Internal Pickups '),
            'domain': [('project_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'item.requisition',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            } 
        
    
    def _compute_cash_requests(self):
        obj = self.env['cash.request']
        for rec in self:
            rec.cash_requests_count = obj.search_count([('project_id', '=', rec.id)])
            
    def _compute_purchase_requests(self):
        obj = self.env['po.requisition']
        for rec in self:
            rec.purchase_requests_count = obj.search_count([('project_id', '=', rec.id)])
    
    
    def open_purchase_requisition(self):
        return {
            'name': _('Purchase Requisition Records'),
            'domain': [('project_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'po.requisition',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            } 
        
    def open_cash_requisition(self):
        return {
            'name': _('Cash Requisition '),
            'domain': [('project_id', '=', self.id)],
            'res_model': 'cash.request',
            'view_mode': 'list,form',
            'view_ids':[('list',False),('form',self.env.ref('psi_engineering.view_transfer_request_form').id)],
            'type': 'ir.actions.act_window',
            'context':{'create':False,'delete':False,'form_view_ref':'psi_engineering.view_transfer_request_form'}
            }   
    
    def _compute_purchase(self):
        obj = self.env['purchase.order']
        for rec in self:
            rec.purchase_count = obj.search_count([('project_id', '=', rec.id)])
    
    def open_purchase(self):
        return {
            'name': _('Purchase Records'),
            'domain': [('project_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            }     
              
    @api.depends("purchase_total_amount", "cash_request_amount")
    def _compute_total_actual_cost(self):
        for rec in self:
            total = rec.purchase_total_amount + rec.cash_request_amount
            rec.total_actual_cost = total

    @api.depends("cash_requests.amount", "cash_requests.state")
    def _compute_cash_request(self):
        for rec in self:
            total = sum(req.amount for req in rec.cash_requests if req.state in ['done', 'cash_out'])
            rec.cash_request_amount = total

            
    @api.depends("purchase_orders.state", "purchase_orders.amount_total", "purchase_orders.amount_untaxed","currency_id")
    def _compute_total_purchases(self):
        for rec in self:
            total = 0
            for purchase in rec.purchase_orders.filtered(lambda x: x.state in ['done', 'purchase']):
                if rec.currency_id:
                    currency = rec.currency_id
                else:
                    currency = self.env.user.company_id.currency_id
                amount = purchase.currency_id._convert(
                    purchase.amount_untaxed, currency)

                total += amount
            rec.purchase_total_amount = total
    
    
    @api.depends('sale_orders.amount_total')
    def _compute_total_sales(self):
        for rec in self:
            total = 0.00
            # Search sale orders related to the current project
            sale_orders = self.env['sale.order'].search([('project_ids', 'in', [rec.id])])
            for sale in sale_orders:
                # Check if the current rec.id is in the project's ids
                if rec.id in sale.project_ids.ids:
                    total += sale.amount_untaxed
            rec.sale_total_amount = total
    
    # @api.depends('sale_orders.amount_total')
    def _compute_total_invoice(self):
        for rec in self:
            total = 0.00
            # Search sale orders related to the current project
            sale_orders = self.env['sale.order'].search([('project_ids', 'in', [rec.id])])
            for sale in sale_orders:
                # Check if the current rec.id is in the project's ids
                if rec.id in sale.project_ids.ids:
                    total += sale.amount_untaxed
            rec.sale_total_amount = total        


    def create_cash_request(self):
        context = {
            'default_project_id': self.id,
        }
        view_id = self.env['ir.model.data'].sudo().check_object_reference(
            'requisitions', 'cash_requisition_form')[1]
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
    def create_item_request(self):
        context = {
            'default_project_id': self.id,
        }
        view_id = self.env['ir.model.data'].sudo().check_object_reference(
            'requisitions', 'item_requisition_form')[1]
        return {
            'name': _("Create Item Requisition"),
            'res_model': 'item.requisition',
            'view_id': view_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': context,
            'type': 'ir.actions.act_window',
        }
    
    def create_purchase_request(self):
        context = {
            'default_project_id': self.id,
        }
        view_id = self.env['ir.model.data'].sudo().check_object_reference(
            'requisitions', 'po_requisition_form')[1]
        return {
            'name': _("Create Purchase Requisition"),
            'res_model': 'po.requisition',
            'view_id': view_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': context,
            'type': 'ir.actions.act_window',
        }    
            

class MilestoneMilestone(models.Model):
    _name = 'milestone.milestone'
    _rec = "name"
    _order = "id desc"
    
    name = fields.Char(string="Name")
    project_id = fields.Many2one('project.project', string="Project")
    deadline = fields.Date(string="Deadline")


   
class ProductSpecification(models.Model):
    _name = 'product.specification'
    _description = 'Lines Product Specification'
    _rec_name = "description"
    
    serial_number = fields.Char(string="S/N")
    site_id = fields.Char( string="Site ID") 
    site_name = fields.Char(string="Site Name")
    sale_id = fields.Many2one('sale.order', string="Sales Order")
    project_id = fields.Many2one('project.project', string="Project")
    project_specification_id = fields.Many2one('project.project', string="Project Specification", help="Reference to the project related to this product specification.")
    lead_id = fields.Many2one('crm.lead', string="Lead")
    product_id = fields.Many2one('product.product' ,string="Item")
    description = fields.Char(string="Description")
    quantity = fields.Float(string='Quantity', default='1.00')
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=False, string='UOM')
    # cost = fields.Float(related="product_id.standard_price", readonly=False, string="Unit Cost")
    price_unit = fields.Float(related="product_id.list_price", readonly=False, string="Sale Price")
    price_subtotal = fields.Float(compute='_compute_subtotal', string='Subtotal', readonly=True, store=True)
    estimation_id = fields.Many2one('estimation.model', string="Estimation", readonly=True)
    state = fields.Selection(related="estimation_id.state", store=True)
    length = fields.Float(string="Length (m)")
    width = fields.Float(string="Width (m)")
    height = fields.Float(string="Height (m)")
    total_dimension = fields.Float(string="Total Dimension (m³)", compute="_compute_total_dimension", store=True)
    # expense_ids = fields.One2many('cash.request', 'lead_id', string="Cash Requisitions")**
    # percentage = fields.Float(string='Margin Percentage%', default=0.00)
    # margin_price = fields.Float(string='Margin', compute='_margin_price')
    # cost_subtotal = fields.Float(compute='_compute_cost_subtotal', string='Cost Subtotal', readonly=True, store=True)
    
    material_costs_ids = fields.One2many('material.costs', 'product_specification_id' , string="Material Costs")
    labour_costs_ids = fields.One2many('labour.costs', 'product_specification_id' , string="Labour Costs")
    overhead_costs_ids = fields.One2many('overhead.costs', 'product_specification_id' , string="Overhead Costs")
    
    total_estimated_cost = fields.Float("Total Estimated Cost", compute="compute_estimation_costs", )
    total_estimated_cost_withmargin = fields.Float("Total Estimated Cost With Margin", compute="compute_estimation_costs")
    
    
    equipment_cost_ids = fields.One2many('equipment.estimated.cost', 'product_specification_id', string='Equipment Estimated Costs')

    # Total estimated cost (computed)
    total_equipment_estimated_cost = fields.Float(string='Total Estimated Cost', compute='_compute_total_estimated_cost', store=True)
    @api.depends('equipment_cost_ids.total_amount')
    def _compute_total_estimated_cost(self):
        for record in self:
            record.total_equipment_estimated_cost = sum(cost.total_amount for cost in record.equipment_cost_ids)
        
    def compute_estimation_costs(self):
        for rec in self:
            estimate= self.env['estimation.model'].search([('product_specification_id','=',rec.id)])
            if estimate:
                
                rec.total_estimated_cost = sum(estimate.mapped('amount_total_estimation_cost'))
                rec.total_estimated_cost_withmargin = sum(estimate.mapped('amount_total_with_margin')) 
            else:
                rec.total_estimated_cost = 0
                rec.total_estimated_cost_withmargin =0

    @api.depends('length', 'width', 'height')
    def _compute_total_dimension(self):
        for rec in self:
            if rec.length > 0 and rec.width > 0 and rec.height > 0:
                rec.total_dimension = rec.length * rec.width * rec.height
            else:
                rec.total_dimension = 0            
    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            subtotal = rec.price_unit * rec.quantity
            rec.update({
                'price_subtotal': subtotal,
            }) 

    def action_view_estimate(self):
        self.ensure_one()
        _logger.info(f"Viewing estimate for Product Specification ID: {self.id}, Lead ID: {self.lead_id.id}")
        if not self.estimation_id:
            estimation = self.env['estimation.model'].create({
                'product_specification_id': self.id,
                'lead_id': self.lead_id.id,
            })
            self.estimation_id = estimation.id
            _logger.info(f"Created new Estimation with ID: {estimation.id}")
        else:
            _logger.info(f"Using existing Estimation with ID: {self.estimation_id.id}")

        return {
            'type': 'ir.actions.act_window',
            'name': 'View Estimation',
            'res_model': 'estimation.model',
            'view_mode': 'form',
            'res_id': self.estimation_id.id,
            'target': 'new',
        }
        
    def action_view_estimate2(self):
        self.ensure_one()
        _logger.info(f"Viewing estimate for Product Specification ID: {self.id}, Lead ID: {self.lead_id.id}")
        if not self.estimation_id:
            estimation = self.env['estimation.model'].create({
                'product_specification_id': self.id,
                'lead_id': self.lead_id.id,
            })
            self.estimation_id = estimation.id
            _logger.info(f"Created new Estimation with ID: {estimation.id}")
        else:
            _logger.info(f"Using existing Estimation with ID: {self.estimation_id.id}")

        return {
            'type': 'ir.actions.act_window',
            'name': 'View Estimation',
            'res_model': 'estimation.model',
            'view_mode': 'form',
            'view_id':self.env.ref('psi_engineering.view_estimation_popup_form').id,
            'res_id': self.estimation_id.id,
            'target': 'current',
        }
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name  
        else:
            self.description = False  

class EquipmentEstimatedCost(models.Model):
    _name = 'equipment.estimated.cost'
    _description = 'Equipment Estimated Cost'

    # Reference to project
    project_id = fields.Many2one('project.project', string='Project',)

    # Reference to CRM Lead
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='cascade')

    # Reference to Product Specification
    product_specification_id = fields.Many2one('product.specification', string='Product Specification')
    
    # Reference to Estimation Model
    estimation_id = fields.Many2one('estimation.model', string='Estimation', ondelete='cascade')
    
    # Product related to the equipment cost
    product_id = fields.Many2one('product.product', string='Product', required=True)
    
    # Description of the cost
    description = fields.Text(string='Description')

    # Unit cost
    unit_cost = fields.Float(string='Unit Cost', required=True)

    # Quantity
    quantity = fields.Float(string='Quantity', required=True)

    # Total amount (computed as unit cost * quantity)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)

    # Date of estimation
    date = fields.Date(string='Estimation Date', default=fields.Date.context_today, required=True)

    @api.depends('unit_cost', 'quantity')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.unit_cost * record.quantity

class MaterialCosts(models.Model):
    _name = 'material.costs'
    _description = 'Lines Material Costs'

    project_id = fields.Many2one('project.project', string="Project")
    product_id = fields.Many2one('product.product', string="Product", domain="[('type', '=', 'consu')]")
    product_specification_id = fields.Many2one('product.specification', string="Project Specification")
    lead_id = fields.Many2one('crm.lead', string="Lead")
    description = fields.Char(string="Description")
    estimation_id = fields.Many2one('estimation.model')
    task_id = fields.Many2one('project.task', string="Task")
    quantity = fields.Float(string="Quantity")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    unit_price = fields.Float(string="Unit Price")
    currency_id = fields.Many2one('res.currency', string="Currency")
    total_cost = fields.Float(string="Total Cost", compute="_compute_total_cost", store=True)
    serial_number = fields.Char(string="Serial Number")
    length = fields.Float(string="Length (m)")
    width = fields.Float(string="Width (m)")
    height = fields.Float(string="Height (m)")
    total_dimension = fields.Float(string="Total Dimension (m³)", compute="_compute_total_dimension", store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_price    

    @api.depends('length', 'width', 'height')
    def _compute_total_dimension(self):
        for rec in self:
            if rec.length > 0 and rec.width > 0 and rec.height > 0:
                rec.total_dimension = rec.length * rec.width * rec.height
            else:
                rec.total_dimension = 0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.description = self.product_id.name  
        else:
            self.description = False    


class LabourCosts(models.Model):
    _name = 'labour.costs'
    _description = 'Lines Labour Costs'

    project_id = fields.Many2one('project.project', string="Project")
    lead_id = fields.Many2one('crm.lead', string="Lead")
    product_id = fields.Many2one('product.product', string="Product", domain="[('type', '=', 'service')]")
    product_specification_id = fields.Many2one('product.specification', string="Project Specification")
    description = fields.Char(string="Labour Description")
    task_id = fields.Many2one('project.task', string="Task")
    number_of_people = fields.Integer(string="Number of People")
    rate_per_day = fields.Float(string="Rate Per Day")
    estimation_id = fields.Many2one('estimation.model')
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    number_of_days = fields.Float(string="Number of Days")
    total_cost = fields.Float(string="Total Cost", compute="_compute_total_cost", store=True)
    serial_number = fields.Char(string="Serial Number")
    name = fields.Char(string='Name')


    @api.depends('number_of_people', 'rate_per_day', 'number_of_days')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.number_of_people * rec.rate_per_day * rec.number_of_days

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """When a product is selected, populate the UOM automatically."""
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name  
        else:
            self.description = False                 


class OverheadCosts(models.Model):
    _name = 'overhead.costs'
    _description = 'Lines Overhead Costs'

    project_id = fields.Many2one('project.project', string="Project")
    product_specification_id = fields.Many2one('product.specification', string="Project Specification")
    product_id = fields.Many2one('product.product', string="Product", domain="[('type', '=', 'service')]")
    lead_id = fields.Many2one('crm.lead', string="Lead")
    description = fields.Char(string="Description")
    task_id = fields.Many2one('project.task', string="Task")
    parent_task_id = fields.Many2one('project.task', string="Parent Task")
    amount = fields.Float(string="Amount")
    quantity = fields.Float(string="Quantity",default=1)  
    estimation_id = fields.Many2one('estimation.model')
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    total_overhead_cost = fields.Float(string="Total Overhead Cost", compute="_compute_total_overhead_cost", store=True)

    @api.depends('amount',"quantity")
    def _compute_total_overhead_cost(self):
        for rec in self:
            rec.total_overhead_cost = rec.amount * rec.quantity

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """When a product is selected, populate the UOM automatically."""
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id        


class EstimatedCosts(models.Model):
    _name = 'estimated.costs'
    _description = 'Lines Estimated Costs'

    project_id = fields.Many2one('project.project', string="Project")
    estimation_id = fields.Many2one('estimation.model')
    lead_id = fields.Many2one('crm.lead', string="Lead")
    product_specification_id = fields.Many2one('product.specification', string="Project Specification")
    description = fields.Char(string="Description")
    task_id = fields.Many2one('project.task', string="Task")
    parent_task_id = fields.Many2one('project.task', string="Parent Task")
    amount = fields.Float(string="Amount")
    total_cost = fields.Float(string="Total Estimated Cost", compute="_compute_total_cost", store=True)

    @api.depends('amount')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.amount


    

class EstimationModel(models.Model):
    _name = 'estimation.model'
    _description = 'Estimation Model'
    _inherit = ['mail.thread']

    name = fields.Char(string="Estimation ID", required=True, copy=False, readonly=True, index=True, default=lambda self: _('New')) 
    product_specification_id = fields.Many2one('product.specification', string="Product Specification")
    lead_id = fields.Many2one('crm.lead', store=True)
    product_id = fields.Many2one(related='product_specification_id.product_id', string="Product", store=True)
    uom_id = fields.Many2one(related='product_specification_id.uom_id', string="Unit of Measure", store=True)
    quantity = fields.Float(related='product_specification_id.quantity', string="Quantity", store=True)
    item_description = fields.Char(string="Item Description")
    detailed_description = fields.Text(string="Detailed Description")
    job_plan = fields.Text(string="Job Plan")
    require_site_survey = fields.Boolean(string="Require Site Survey")
    require_installation = fields.Boolean(string="Require Installation")
    require_design = fields.Boolean(string="Require Design")
    no_boms_required = fields.Boolean(string="No BOMs Required")
    size = fields.Float(string="Size")
    size_uom = fields.Many2one('uom.uom', string="Size UOM")
    remarks = fields.Text(string="Remarks")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")

    material_costs_ids = fields.One2many('material.costs', 'estimation_id', string="Material Costs")
    labour_costs_ids = fields.One2many('labour.costs', 'estimation_id', string="Labour Costs")
    overhead_costs_ids = fields.One2many('overhead.costs', 'estimation_id', string="Overhead Costs")

    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.user.company_id.currency_id, tracking=True)

    amount_total_material_costs = fields.Monetary(string="Total Material Costs", compute="_compute_total_material_costs", store=True)
    amount_total_labour_costs = fields.Monetary(string="Total Labour Costs", compute="_compute_total_labour_costs", store=True)
    amount_total_overhead_costs = fields.Monetary(string="Total Overhead Costs", compute="_compute_total_overhead_costs", store=True)
    amount_total_estimation_cost = fields.Monetary(string="Total Estimated Costs", compute="_compute_total_estimation_cost", store=True)
    margin_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string="Margin Type", default='fixed', required=True)
    margin_value = fields.Float(string="Margin Value", default=0.0)
    amount_total_with_margin = fields.Monetary(string="Total with Margin", compute="_compute_total_with_margin", store=True)

    equipment_cost_ids = fields.One2many('equipment.estimated.cost', 'estimation_id', string='Equipment Estimated Costs')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='State',
        default='draft',
        tracking=True,
        required=True
    )

    def action_submit(self):
        """Transition the state to 'submitted'."""
        for record in self:
            record.state = 'submitted'

    def action_approve(self):
        """Transition the state to 'approved'."""
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        """Transition the state to 'rejected'."""
        for record in self:
            record.state = 'rejected'

    def action_reset_to_draft(self):
        """Transition the state back to 'draft'."""
        for record in self:
            record.state = 'draft'

    # Total estimated cost (computed)
    total_estimated_cost = fields.Float(string='Total  Estimated Equipment Cost', compute='_compute_total_estimated_cost', store=True)
    @api.depends('equipment_cost_ids.total_amount','equipment_cost_ids')
    def _compute_total_estimated_cost(self):
        for record in self:
            record.total_estimated_cost = sum(cost.total_amount for cost in record.equipment_cost_ids)
        # for record in self:
        #     record.total_amount = record.unit_cost * record.quantity

    @api.model
    def create(self, vals):
        """ Override create method to generate sequence for Estimation ID """
        if vals.get('name', _('New')) == _('New'):
            sequence = self.env['ir.sequence'].sudo().search([('code', '=', 'estimation.model')], limit=1)
            if not sequence:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': 'Estimation Model Sequence',
                    'code': 'estimation.model',
                    'prefix': 'E',
                    'padding': 5,
                    'number_increment': 1,
                })
            vals['name'] = sequence.next_by_code('estimation.model') or _('New')
        return super(EstimationModel, self).create(vals)

    @api.depends('material_costs_ids.total_cost')
    def _compute_total_material_costs(self):
        """ Compute total material costs """
        for record in self:
            total = sum(material.total_cost for material in record.material_costs_ids)
            record.amount_total_material_costs = total

    @api.depends('labour_costs_ids.total_cost')
    def _compute_total_labour_costs(self):
        """ Compute total labour costs """
        for record in self:
            total = sum(labour.total_cost for labour in record.labour_costs_ids)
            record.amount_total_labour_costs = total

    @api.depends('overhead_costs_ids.total_overhead_cost')  
    def _compute_total_overhead_costs(self):
        """ Compute total overhead costs """
        for record in self:
            total = sum(overhead.total_overhead_cost for overhead in record.overhead_costs_ids)
            record.amount_total_overhead_costs = total

    @api.depends('amount_total_material_costs', 'amount_total_labour_costs', 'amount_total_overhead_costs','total_estimated_cost',)
    def _compute_total_estimation_cost(self):
        """ Compute total estimated costs (material + labour + overhead+equipment) """
        for record in self:
            record.amount_total_estimation_cost = (
                record.amount_total_material_costs +
                record.amount_total_labour_costs +
                record.amount_total_overhead_costs +
                record.total_estimated_cost
            )

    @api.depends('amount_total_estimation_cost', 'margin_type', 'margin_value')
    def _compute_total_with_margin(self):
        """ Compute total with margin based on margin type """
        for record in self:
            if record.margin_type == 'fixed':
                record.amount_total_with_margin = record.amount_total_estimation_cost + record.margin_value
            elif record.margin_type == 'percentage':
                margin_amount = record.amount_total_estimation_cost * (record.margin_value / 100)
                record.amount_total_with_margin = record.amount_total_estimation_cost + margin_amount
            else:
                record.amount_total_with_margin = record.amount_total_estimation_cost

    @api.onchange('margin_type', 'margin_value', 'amount_total_estimation_cost')
    def _onchange_margin(self):
        """ Recompute total with margin when margin fields change """
        self._compute_total_with_margin()

    def _check_lead_and_product_specification(self):
        """ Ensure the lead in the estimation matches the lead in the product specification """
        for record in self:
            if record.lead_id != record.product_specification_id.lead_id:
                raise ValidationError("The Lead in the Estimation must match the Lead in the Product Specification.")




class CashRequest(models.Model):
    
    _inherit = "cash.request"

    project_id = fields.Many2one("project.project", string="Project")
    url = fields.Char("URL", compute="compute_url")
    def compute_url(self):
        for rec in self:
            base_url = self.env['ir.config_parameter'].sudo().search(
                [('key', '=', 'web.base.url')], limit=1)
            url = base_url.value + "/web#id=" + \
                str(rec.id)+"&model=cash.request&view_type=form"
            rec.url = url      
            
    def btn_mv_submitted(self):
        for rec in self:
            if rec.amount <= 0.00:
                raise models.ValidationError('Cannot request for zero (0) amounts of money!!!')
            else:
                rec.write({
                    'requested_by' : self.env.uid,
                    'department_id' : self.env.user.employee_id.department_id.id if self.env.user.employee_id.department_id else False,
                    'state': 'submitted',
                    'date': date.today(),
                })  
                group = self.env.ref('requisitions.cash_group_manager') 
                for user in group.users:
                    template = self.env.ref('psi_engineering.cash_requisition_email_template')            
                    email_to = user.partner_id.email or user.email
                    if not email_to:
                        continue
                    self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True, email_values={
                        'email_to': email_to,
                    })         



class CashRequestLine(models.Model):
    _inherit = "cash.request.lines"

    project_id = fields.Many2one(
        "project.project", string="Project", related="cash_id.project_id", store=True)

class ItemRequisition(models.Model):
    
    _inherit = "item.requisition"

    project_id = fields.Many2one("project.project", string="Project")
    
   

class ItemRequisitionLine(models.Model):
    _inherit = "item.requisition.order.line"

    # cost = fields.Float(related="product_id.standard_price", readonly=False, store=True, string="Unit Cost")
    cost = fields.Float(readonly=False, string="Unit Cost")
    price_unit = fields.Float(related="product_id.list_price", readonly=False, store=True, string="Sale Price")
    price_subtotal = fields.Float(compute='_compute_subtotal', string='Subtotal', readonly=True, store=True)
    cost_subtotal = fields.Float(compute='_compute_cost_subtotal', string='Cost Subtotal', readonly=True, store=True)

    @api.depends('product_qty', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            subtotal = rec.price_unit * rec.product_qty
            rec.update({
                'price_subtotal': subtotal,
            }) 
    @api.depends('product_qty', 'cost')
    def _compute_cost_subtotal(self):
        for rec in self:
            subtotal = rec.cost * rec.product_qty
            rec.update({
                'cost_subtotal': subtotal,
            })         


class PurchaseOrder(models.Model):
    
    _inherit = "purchase.order"

    project_id = fields.Many2one("project.project", string="Project")
    
    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.project_id:
            vals['project_id'] = self.project_id.id
        return vals

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    project_id = fields.Many2one(
        "project.project", string="Project", related="order_id.project_id", store=True)
    budget_line_id = fields.Many2one("budget.line", string="Budget Line")
    budget_id = fields.Many2one("budget.analytic", related="order_id.budget_id", store=True)
    show_budget_warning = fields.Boolean("Show Budget Warning", compute="compute_show_budget_warning", store=True)
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
    
    @api.depends("order_id.state",'price_subtotal','price_total','budget_line_id','remaining_budget')
    def compute_show_budget_warning(self):
        for rec in self:
            if not rec.budget_line_id:
                rec.show_budget_warning = False
            elif rec.price_total > rec.budget_line_id.remaining_amount:
                rec.show_budget_warning = True
            else:
                rec.show_budget_warning = False
    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        vals = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        vals['project_id'] = self.project_id.id if self.project_id else False
        return vals
    def _prepare_account_move_line(self, move=False):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        vals['project_id'] = self.project_id.id if self.project_id else False
        if not self.analytic_distribution or self.analytic_distribution == {}:
            if self.project_id and self.project_id.account_id:
                vals['analytic_distribution'] = {self.project_id.account_id:100}
        return vals
    
    remaining_budget = fields.Float(
        string="Remaining Budget", compute='_compute_remaining_budget', store=True)

    @api.depends('budget_line_id')
    def _compute_remaining_budget(self):
        """ Compute the remaining budget for the selected budget line """
        for line in self:
            if line.budget_line_id:
                # Assume `achieved_amount` is the amount already spent and `budget_amount` is the budgeted amount
                line.remaining_budget = line.budget_line_id.budget_amount - \
                    line.budget_line_id.achieved_amount
            else:
                line.remaining_budget = 0.0

class AccountMove(models.Model):
    _inherit = "account.move"

    project_id = fields.Many2one(
        "project.project", string="Project")
class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    project_id = fields.Many2one(
        "project.project", string="Project", related="picking_id.project_id", store=True)

