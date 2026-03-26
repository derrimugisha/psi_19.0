from odoo import models, fields, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError , UserError
import base64
import pandas as pd
import logging
_logger = logging.getLogger(__name__)

class CustomFleetVehicle(models.Model):
    _name = 'custom.fleet.vehicle'
    _inherits = {'fleet.vehicle': 'vehicle_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Custom Fleet Vehicle'

    vehicle_id = fields.Many2one('fleet.vehicle', required=True, ondelete='cascade')
    in_out_state = fields.Selection([
        ('draft', 'Draft'),
        ('checked_out', 'Checked Out'),
        ('checked_in', 'Checked In')
    ], string="Checked In / Out Status", default='draft', tracking=True)

    service_type = fields.Selection([
        ('Van Sales', 'Van Sales'),
        ('Staff Vehicle', 'Staff Vehicle'),
        ('Office Operations', 'Office Operations'),
    ], string="Service Type")

    staff_member = fields.Many2one('hr.employee', string="Staff Member")
    stock_location = fields.Many2one('stock.location', string="Stock Location", domain=[('usage','=','internal')])

    odometer_logs_count = fields.Integer(string="Odometer logs count", compute="_compute_odometer_logs_count")

    @api.depends('log_services')
    def _compute_odometer_logs_count(self):
        for item in self:
            item.odometer_logs_count = self.env['fleet.vehicle.odometer'].search_count([('vehicle_id','=', self.vehicle_id.id)])

    fuel_expenses = fields.One2many('cash.request', 'vehicle_id', domain=[('vehicle_request_type', '=', 'Fuel Requisition')], string="Fuel Requests")
    fuel_expenses_value = fields.Char(string="Fuel Expense Value", compute='_compute_fuel_expense_value')
    fuel_expenses_count = fields.Integer(string="Fuel Expense Count", compute='_compute_fuel_expense_value')

    servicing_expenses = fields.One2many('cash.request', 'vehicle_id', domain=[('vehicle_request_type', '=', 'Service Requisition')], string="Service Requests")
    servicing_expenses_value = fields.Char(string="Servicing Expense Value", compute='_compute_servicing_expense_value')
    servicing_expenses_count = fields.Integer(string="Servicing Expense Count", compute='_compute_servicing_expense_value')
    
    repair_expenses = fields.One2many('cash.request', 'vehicle_id', domain=[('vehicle_request_type', '=', 'Repair Requisition')], string="Repairs Requests")
    repair_expenses_value = fields.Char(string="Repair Expense Value", compute='_compute_repair_expense_value')
    repair_expenses_count = fields.Integer(string="Repair Expense Count", compute='_compute_repair_expense_value')
    item_requests_count = fields.Integer(string="Item Request Count", compute="_compute_item_requests")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    analytic_account_balance = fields.Char(string="Analytic Balance",compute="_compute_analytic_account_balance")

    @api.depends('analytic_account_id')
    def _compute_analytic_account_balance(self):
        for record in self:
            balance = sum(record.analytic_account_id.line_ids.mapped('amount'))
            # balance = sum(rec.amount for rec in record.analytic_account_id.line_ids)
            balance = str("{:,.2f}".format(balance)) + " " + str(record.currency_id.symbol)
            record.analytic_account_balance = balance
            

    @api.depends('fuel_expenses')
    def _compute_fuel_expense_value(self):
        """Compute the total value and count of related fuel expenses."""
        for record in self:
            total_value = sum(expense.amount for expense in record.fuel_expenses)
            total_value = str("{:,.2f}".format(total_value)) + " " + str(record.currency_id.symbol)
            record.fuel_expenses_value = total_value
            record.fuel_expenses_count = len(record.fuel_expenses)            

    @api.model
    def create(self, vals):
        # Find or validate the analytic plan first
        default_plan = self.env['account.analytic.plan'].search([], limit=1)
        if not default_plan:
            raise UserError("No default Analytic Plan found. Please configure an Analytic Plan.")

        record = super(CustomFleetVehicle, self).create(vals)

        license_plate = record.vehicle_id.license_plate or ''
        name = record.vehicle_id.display_name or ''  # Use display_name instead of name

        if license_plate or name:
            analytic_name = f"{license_plate} - {name}" if license_plate and name else (license_plate or name)
            analytic_vals = {
                'name': analytic_name.strip(),
                'company_id': record.company_id.id or self.env.company.id,  # Use the record's company_id
                'plan_id': default_plan.id,
            }
            analytic_account = self.env['account.analytic.account'].create(analytic_vals)
            record.analytic_account_id = analytic_account

        return record
    

    def create_item_request(self):
        context = {
            'default_vehicle_id': self.id,
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
    
    def _compute_item_requests(self):
        obj = self.env['item.requisition']
        for rec in self:
            rec.item_requests_count = obj.search_count([('vehicle_id', '=', rec.id)])
            
    def open_item_requisition(self):
        return {
            'name': _('Item Requisition Records'),
            'domain': [('vehicle_id', '=', self.id)],
            'view_type': 'form',
            'res_model': 'item.requisition',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            }

    @api.depends('ins_outs')
    def _compute_ins_outs_count(self):
        for item in self:
            item.ins_outs_count = len(item.ins_outs)

    @api.depends('other_expenses')
    def _compute_other_expenses_count(self):
        for item in self:
            item.other_expenses_count = len(item.other_expenses)



    @api.depends('fuel_expenses')
    def _compute_fuel_expense_value(self):
        """Compute the total value and count of related fuel expenses."""
        for record in self:
            total_value = sum(expense.amount for expense in record.fuel_expenses)
            total_value = str("{:,.2f}".format(total_value)) + " " + str(record.currency_id.symbol)
            record.fuel_expenses_value = total_value
            record.fuel_expenses_count = len(record.fuel_expenses)

    @api.depends('servicing_expenses')
    def _compute_servicing_expense_value(self):
        """Compute the total value and count of related servicing expenses."""
        for record in self:
            total_value = sum(expense.amount for expense in record.servicing_expenses)
            total_value = str("{:,.2f}".format(total_value)) + " " + str(record.currency_id.symbol)
            record.servicing_expenses_value = total_value
            record.servicing_expenses_count = len(record.servicing_expenses)

    @api.depends('repair_expenses')
    def _compute_repair_expense_value(self):
        """Compute the total value and count of related repair expenses."""
        for record in self:
            total_value = sum(expense.amount for expense in record.repair_expenses)
            total_value = str("{:,.2f}".format(total_value)) + " " + str(record.currency_id.symbol)
            record.repair_expenses_value = total_value
            record.repair_expenses_count = len(record.repair_expenses)

    def create_fuel_requisition(self):
        """Open the form view for fuel requisition."""
        return {
            'name': _('Create Fuel Requisition'),
            'view_mode': 'form',
            'res_model': 'cash.request',
            'view_id': self.env.ref('psi_engineering.vehicle_cash_requisition_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_vehicle_id': self.id,
                'default_vehicle_request_type': 'Fuel Requisition',
                'default_current_mileage' : self.odometer,
                'default_tom_card_number': self.tom_card_number,
            },
            'target': 'new',
        }
    
    def create_service_requisition(self):
        """Open the form view for service requisition."""
        return {
            'name': _('Create Service Requisition'),
            'view_mode': 'form',
            'res_model': 'cash.request',
            'view_id': self.env.ref('psi_engineering.vehicle_cash_requisition_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_vehicle_id': self.id,
                'default_vehicle_request_type': 'Service Requisition',
                'default_current_mileage' : self.odometer,
            },
            'target': 'new',
        }
    
    def create_repair_requisition(self):
        """Open the form view for repair requisition."""
        return {
            'name': _('Create Repair Requisition'),
            'view_mode': 'form',
            'res_model': 'cash.request',
            'view_id': self.env.ref('psi_engineering.vehicle_cash_requisition_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_vehicle_id': self.id,
                'default_vehicle_request_type': 'Repair Requisition',
                'default_current_mileage' : self.odometer,
            },
            'target': 'new',
        }
    
    def open_fuel_requisitions(self):
        """Opens fuel requisition list and form views."""
        return {
            'name': _('Fuel Requisitions'),
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('psi_engineering.vehicle_cash_requisition_list').id, 'list'),
                (self.env.ref('psi_engineering.vehicle_cash_requisition_form').id, 'form'),
            ],
            'res_model': 'cash.request',
            'type': 'ir.actions.act_window',
            'domain': [('vehicle_id', '=', self.id),('vehicle_request_type', '=', 'Fuel Requisition')],
            'context': {'default_vehicle_id': self.id, 'default_vehicle_request_type': 'Fuel Requisition'},
            'target': 'current',
        }
    
    def action_open_analytic_items(self):
        self.ensure_one()
        return {
            'name': 'Analytic Items',
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('analytic.view_account_analytic_line_tree').id, 'list'),
                (self.env.ref('analytic.view_account_analytic_line_form').id, 'form'),
            ],
            'domain': [('account_id', '=', self.analytic_account_id.id)],
            'context': {'default_account_id': self.analytic_account_id.id},
            'target': 'current',
        }
    
    def open_service_requisitions(self):
        """Opens service requisition list and form views."""
        return {
            'name': _('Service Requisitions'),
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('psi_engineering.vehicle_cash_requisition_list').id, 'list'),
                (self.env.ref('psi_engineering.vehicle_cash_requisition_form').id, 'form'),
            ],
            'res_model': 'cash.request',
            'type': 'ir.actions.act_window',
            'domain': [('vehicle_id', '=', self.id),('vehicle_request_type', '=', 'Service Requisition')],
            'context': {'default_vehicle_id': self.id, 'default_vehicle_request_type': 'Service Requisition'},
            'target': 'current',
        }
    
    def open_repair_requisitions(self):
        """Opens repair requisition list and form views."""
        return {
            'name': _('Reapir Requisitions'),
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('psi_engineering.vehicle_cash_requisition_list').id, 'list'),
                (self.env.ref('psi_engineering.vehicle_cash_requisition_form').id, 'form'),
            ],
            'res_model': 'cash.request',
            'type': 'ir.actions.act_window',
            'domain': [('vehicle_id', '=', self.id),('vehicle_request_type', '=', 'Repair Requisition')],
            'context': {'default_vehicle_id': self.id, 'default_vehicle_request_type': 'Repair Requisition'},
            'target': 'current',
        }


    
   
    tom_card_number = fields.Char("Tom Card Number")
    next_service_mileage = fields.Float("Next Service Mileage")

    def open_odometer_logs(self):
        """Opens odometer logs."""
        return {
            'name': _('Odometer Logs'),
            'view_mode': 'list,form',
            'res_model': 'fleet.vehicle.odometer',
            'type': 'ir.actions.act_window',
            'domain': [('vehicle_id', '=', self.vehicle_id.id)],
            'context': {'default_vehicle_id': self.vehicle_id.id},
            'target': 'current',  # Opens in the current window
        }

# class FleetVehicleOdometer(models.Model):
#     _inherit = "fleet.vehicle.odometer"

#     @api.model_create_multi
#     def create(self, vals):
#         vehicle_id = vals.get('vehicle_id')
#         current_reading = vals.get('value')

#         if vehicle_id and current_reading is not None:
#             # Get the maximum previous odometer reading for the vehicle
#             previous_reading = self.search([
#                 ('vehicle_id', '=', vehicle_id)
#             ], order='value desc', limit=1).value

#             # Check if the current reading is less than the previous reading
#             if previous_reading and current_reading < previous_reading:
#                 raise models.ValidationError(
#                     f"The new odometer reading provided cannot be less than the previous reading of {previous_reading}."
#                 )

#         return super(FleetVehicleOdometer, self).create(vals)

class FleetVehicleOdometer(models.Model):
    _inherit = "fleet.vehicle.odometer"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:  # Iterate through the list of dictionaries
            vehicle_id = vals.get('vehicle_id')
            current_reading = vals.get('value')

            if vehicle_id and current_reading is not None:
                # Get the maximum previous odometer reading for the vehicle
                previous_reading = self.search([
                    ('vehicle_id', '=', vehicle_id)
                ], order='value desc', limit=1).value

                # Check if the current reading is less than the previous reading
                if previous_reading and current_reading < previous_reading:
                    raise models.ValidationError(
                        f"The new odometer reading provided cannot be less than the previous reading of {previous_reading}."
                    )

        return super(FleetVehicleOdometer, self).create(vals_list)  # Pass the entire list to super


class VehicleCashRequisition(models.Model):
    _inherit = 'cash.request'

    STATUS = [
        ('draft', 'Draft'),
        ('submitted', 'PM Approval'),
        ('procurement_approved', 'Procurement Approval'),
        ('finance_approved', 'Finance Approval'),
        ('md_approval', 'MD Approval'),
        ('cash_out', 'Cash Out'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ]

    state = fields.Selection(STATUS, default='draft',
                             tracking=True, index=True)

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)

    vehicle_id = fields.Many2one('custom.fleet.vehicle', string="Vehicle")
    tom_card_number = fields.Char("Tom Card Number")
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id.id, tracking=True,copy=True)
    move_count = fields.Integer(
        string="Journal Entries")
    purchase_receipt_count = fields.Integer(
        string="Purchase Receipts")
    vendor_bill_count = fields.Integer(
        string="Vendor Bills")
    lead_id = fields.Many2one('crm.lead', string="Related Lead", readonly=True)
    employee_threshold = fields.Float(
        string="Threshold" , readonly=True)
    car_manager_id = fields.Many2one('res.users', string="Car Manager", required=False)

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            if self.vehicle_id.manager_id:
                self.car_manager_id = self.vehicle_id.manager_id
            else:
                self.car_manager_id = self.env.user  # fallback default

    @api.constrains('vehicle_id', 'car_manager_id')
    def _check_car_manager_required(self):
        for record in self:
            if record.vehicle_id and not record.vehicle_id.manager_id and not record.car_manager_id:
                raise ValidationError("Please select a Car Manager since the vehicle has no assigned manager.")

    
    def cash_request(self):
        """
        This Method is used to cash out a requisition.
        """
        pay_obj = self.env['account.move']

        if self.amount <= 0.00:
            raise models.ValidationError('You cannot make a payment of amount zero(0)')
        for data in self:
            if not data.user:
                raise models.ValidationError('Cannot make this payment! You need approval')
            else:
                prd_account_id = self._default_account()

                inv_lines = []
                for rec in data.line_ids:
                    inv_line_values = {
                        'name': "Requisition for " + str(rec.product_id.name),
                        'quantity': rec.qty,
                        'price_unit': rec.unit_price,
                        'account_id': rec.account_id.id if rec.account_id else self._default_account(),
                        'analytic_distribution': {rec.analytic_account_id.id : 100} if rec.analytic_account_id else {},

                    }
                    inv_lines.append((0, 0, inv_line_values))

                inv_values = {
                    'move_type': 'in_receipt',
                    'requisition_id': self.id,
                    'partner_id': data.requested_by.partner_id.id,
                    'invoice_date': data.date,
                    'invoice_line_ids': inv_lines
                }
                acc_id = pay_obj.create(inv_values)
                data.write({'acc_id': acc_id.id})
                acc_id.action_post()

            self.write({'state': 'done'})
        return 0

    

    @api.onchange('vehicle_id')
    def set_odometer_reading(self):
        for item in self:
            if item.vehicle_id:
                item.current_mileage = item.vehicle_id.odometer
    
    vehicle_request_type = fields.Selection([
        ('Fuel Requisition','Fuel Requisition'),
        ('Service Requisition','Service Requisition'),
        ('Repair Requisition','Repair Requisition'),
    ])

    rate_per_litre = fields.Float("Rate Per/L")
    litres = fields.Float("Litres")

    @api.onchange('rate_per_litre', 'litres')
    def set_fuel_cost(self):
        for item in self:
            if item.rate_per_litre > 0 and item.litres > 0:
                item.cost = item.rate_per_litre * item.litres
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)

    cost = fields.Monetary(currency_field="currency_id", string="Cost")

    sr_vendor = fields.Many2one('res.partner', string="Vendor")
    current_mileage = fields.Float("Current Mileage")
    next_service_mileage = fields.Float("Next Service Mileage")
    description = fields.Text("Description")

    #To submit requisition for approval
    def btn_mv_submitted(self):
        for rec in self:
            if rec.amount <= 0.00 and not rec.vehicle_request_type:
                raise models.ValidationError('Cannot request for zero (0) amounts of money!!!')
            
            if rec.vehicle_request_type:
                product_id = False
                if rec.vehicle_request_type == 'Fuel Requisition':
                    fuel_product = self.env['ir.config_parameter'].sudo().get_param('psi_engineering.fuel_product')
                    if not fuel_product:
                        raise models.ValidationError("Please configure the fuel product in accounting settings first!")
                    
                    product_id = int(fuel_product)

                if rec.vehicle_request_type == 'Service Requisition':
                    servicing_product = self.env['ir.config_parameter'].sudo().get_param('psi_engineering.servicing_product')
                    if not servicing_product:
                        raise models.ValidationError("Please configure the servicing product in accounting settings first!")
                    
                    product_id = int(servicing_product)

                if rec.vehicle_request_type == 'Repair Requisition':
                    repair_product = self.env['ir.config_parameter'].sudo().get_param('psi_engineering.repair_product')
                    if not repair_product:
                        raise models.ValidationError("Please configure the repairs product in accounting settings first!")

                    product_id = int(repair_product)

                # cash_line = self.env['cash.request.lines'].create({
                #     'cash_id' : rec.id,
                #     'product_id': product_id,
                #     'description' : (rec.vehicle_request_type + " for "+rec.vehicle_id.name),
                #     'item': (rec.vehicle_request_type + " for "+rec.vehicle_id.name),
                #     'qty' : 1,
                #     'currency_id' : rec.currency_id.id,
                #     'unit_price' : rec.cost,
                #     'analytic_account_id': rec.vehicle_id.analytic_account_id.id,
                # })

            rec.write({
                'requested_by' : self.env.uid,
                'state': 'submitted',
                'date': date.today(),
            })

            if rec.next_service_mileage:
                rec.vehicle_id.next_service_mileage = rec.next_service_mileage

    def pm_approval(self):
        for rec in self:
            if rec.state == 'submitted':
                rec.write({'state': 'procurement_approved'})
            else:
                raise models.ValidationError('Cannot approve this requisition! It is not in the correct state')
            
    def procurement_approval(self):
        for rec in self:
            if rec.state == 'procurement_approved':
                rec.write({'state': 'finance_approved'})
            else:
                raise models.ValidationError('Cannot approve this requisition! It is not in the correct state')        
            
    def finance_approval(self):
        for rec in self:
            if rec.state == 'finance_approved':
                rec.write({'state': 'md_approval'})
            else:
                raise models.ValidationError('Cannot approve this requisition! It is not in the correct state')        
            
    def md_approval(self):
        for rec in self:
            rec.write({
                'state': 'cash_out',
                'user':self.env.user.id,
                'approval_date':fields.Datetime.now()
            })

    def cancel_request(self):
        for rec in self:
            rec.state = 'cancel'

    def reset_request(self):
        for rec in self:
            rec.state = 'draft'                

    def create_purchase_receipt(self, payment_date):
        """
        This Method is used to cash out a requisition.
        """
        pay_obj = self.env['account.move']
        payment_date = fields.Date.today()

        if self.amount <= 0.00:
            raise models.ValidationError('You cannot Make a payment of amount Zero(0)')
        for data in self:
            if not data.user:
                raise models.ValidationError('Cannot make this payment. you need approval')
            else:
                inv_lines = []
                for rec in data.line_ids:
                    if rec.product_id and rec.unit_price > 0:
                        inv_line_values = {
                            'product_id' : rec.product_id.id,
                            'name': "Requisition for " + rec.product_id.name,
                            'quantity': rec.qty,
                            'price_unit': rec.unit_price,
                            'analytic_distribution': {rec.analytic_account_id.id : 100} if rec.analytic_account_id else {},
                        }

                        if rec.account_id:
                            inv_line_values['account_id'] = rec.account_id.id
                            
                        inv_lines.append((0, 0, inv_line_values))
                    else:
                        continue

                if not data.acc_id:
                    
                    if len(inv_lines) > 0:
                        inv_values = {
                            'partner_id': data.requested_by.partner_id.id,
                            'move_type': 'in_receipt',
                            'requisition_id': self.id,
                            'currency_id': data.currency_id.id,
                            'invoice_date': payment_date,
                            # 'invoice_date_due': self.date,
                            'invoice_line_ids': inv_lines
                        }
                        acc_id = pay_obj.create(inv_values)
                        for line in acc_id.invoice_line_ids:
                            _logger.info(f"Line {line.id}: account_id={line.account_id.id}, display_type={line.display_type}")
                        data.write({'acc_id': acc_id.id})
                        acc_id.action_post()

                    else:
                        raise models.ValidationError('No valid line items to cash out!')
                else:
                    data.acc_id.write({
                        'invoice_date': payment_date,
                        'invoice_line_ids': [(5, 0, 0)] + inv_lines,  # Remove existing lines and add new ones
                        'currency_id': data.currency_id.id,  # Update the currency
                    })

                    if data.acc_id.state == 'draft':
                        data.acc_id.action_post()

class VehicleCashRequestLines(models.Model):
    _inherit = 'cash.request.lines'
    
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id.id, tracking=True,copy=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    product_id = fields.Many2one(
        "product.product", string="Product")
    budget_id = fields.Many2one("budget.analytic", string="Budget", tracking=True)
    budget_line_id = fields.Many2one(
        'budget.line', string="Budget Line")
    remaining_budget = fields.Float(
        string="Remaining Budget", store=True)

    @api.onchange('product_id')
    def set_account(self):
        for item in self:
            if item.product_id:
                if item.product_id.categ_id:
                    if item.product_id.categ_id.property_account_expense_categ_id:
                        item.account_id = item.product_id.categ_id.property_account_expense_categ_id.id



    
class VehicleExpense(models.Model):
    _name = 'vehicle.expense'
    _description = 'Other Vehicle Expense'

    name = fields.Char(string="Vehicle Expense", required=True)
    description = fields.Text(string="Description")



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fuel_product = fields.Many2one("product.product", string="Fuel Product", config_parameter="psi_engineering.fuel_product")
    servicing_product = fields.Many2one("product.product", string="Servicing Product", config_parameter="psi_engineering.servicing_product")
    repair_product = fields.Many2one("product.product", string="Repairs Product", config_parameter="psi_engineering.repair_product")

class ItemRequisition(models.Model):
    
    _inherit = "item.requisition"
    
    vehicle_id = fields.Many2one('custom.fleet.vehicle', string="Vehicle")
    compute_required = fields.Boolean('Compute Required', compute="_compute_required")
    
    # @api.depends('vehicle_id')
    # def _compute_required(self):
    #     for record in self:
    #         if record.vehicle_id:
    #            record.compute_required = True

    @api.depends('vehicle_id')
    def _compute_required(self):
        for record in self:
            record.compute_required = bool(record.vehicle_id)