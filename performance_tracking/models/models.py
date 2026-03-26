# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)
import ast
from datetime import datetime, time
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _performance_get_default_domain(self, mailing):
            return ['&', ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]

class Performance(models.Model):
    _name = 'performance'
    _description = 'Employee Performance'
    _rec_name = "employee_id"


    # name = fields.Char(string='Performance Name', required=True)
    employee_id = fields.Many2one('res.users', string='Employee', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    performance_line_ids = fields.One2many('performance.line', 'performance_id', string='Performance Lines')
    
    @api.model
    def action_compute_cron_progress(self):
        performances = self.search([])
        for rec in performances:
            if rec.performance_line_ids:
                for line in rec.performance_line_ids:
                    line._compute_done()
                    line._compute_percentage()
                    
    def action_compute_progress(self):
        for rec in self:
            if rec.performance_line_ids:
                for line in rec.performance_line_ids:
                    line._compute_done()
                    line._compute_percentage()


class PerformanceLine(models.Model):
    _name = 'performance.line'
    _description = 'Performance Line'
    
    
    def _get_allowed_models(self):
        config = self.env['ir.config_parameter'].sudo()
        model_ids_str = config.get_param('performance.allowed_model_ids')
        if model_ids_str:
            model_ids = [int(mid) for mid in model_ids_str.split(',') if mid]
            return [('id', 'in', model_ids)]
        return []
    
    model_id = fields.Many2one(
        'ir.model',
        string='Model Name',
        required=True,
        domain=_get_allowed_models,
        ondelete='cascade',
    )

    # model_id = fields.Many2one('ir.model', string='Model Name', required=True,ondelete='cascade',
    #                                domain="[('model', 'in', ['account.move', 'crm.lead', 'mail.activity', 'project.task', 'sale.order'])]",)
    performance_id = fields.Many2one('performance', string='Performance', required=True)
    target = fields.Integer(string='Target', required=True)
    done = fields.Integer(string='Done', compute='_compute_done', store=True)
    percentage = fields.Float(string='Percentage', compute='_compute_percentage', store=True)
    model_domain = fields.Char(
        string='Domain',
        compute='_compute_model_domain', readonly=False, store=True)
    model_name = fields.Char(
        string='Model Name',
        related='model_id.model', readonly=True, related_sudo=True)
    model_real = fields.Char(
        string='Real Model', compute='_compute_model_real')

    
    @api.depends('model_id')
    def _compute_model_real(self):
        for rec in self:
            rec.model_real = rec.model_id.model

    
    def _get_default_model_domain(self):
        model_domain = []
        if hasattr(self.env[self.model_name], '_performance_get_default_domain'):
            model_domain = self.env[self.model_name]._performance_get_default_domain(self)
        return model_domain
    
    
    @api.depends('model_id')
    def _compute_model_domain(self):
        for rec in self:
            if not rec.model_id or not rec.performance_id:
                rec.model_domain = ''
                continue

            base_domain = []
            if hasattr(self.env[rec.model_id.model], '_performance_get_default_domain'):
                base_domain = self.env[rec.model_id.model]._performance_get_default_domain(rec)

            emp = rec.performance_id.employee_id
            start_date = rec.performance_id.start_date
            end_date = rec.performance_id.end_date

            start_dt = datetime.combine(start_date, time.min) if start_date else None
            end_dt = datetime.combine(end_date, time.max) if end_date else None

            # Format to string (ISO 8601)
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S') if start_dt else None
            end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S') if end_dt else None

            additional_domain = []
            model = rec.model_id.model

            if model == 'account.move':
                additional_domain += [('user_id', '=', emp.id)]
                if start_str and end_str:
                    additional_domain += [('invoice_date', '>=', start_str), ('invoice_date', '<=', end_str)]

            elif model == 'crm.lead':
                additional_domain += [('user_id', '=', emp.id)]
                if start_str and end_str:
                    additional_domain += [('create_date', '>=', start_str), ('create_date', '<=', end_str)]

            elif model == 'mail.activity':
                additional_domain += [('user_id', '=', emp.id)]
                if start_date and end_date:
                    additional_domain += [('date_deadline', '>=', start_date.isoformat()), ('date_deadline', '<=', end_date.isoformat())]

            elif model == 'project.task':
                additional_domain += [('user_ids', 'in', emp.id)]
                if start_str and end_str:
                    additional_domain += [('create_date', '>=', start_str), ('create_date', '<=', end_str)]

            elif model == 'sale.order':
                additional_domain += [('user_id', '=', emp.id)]
                if start_str and end_str:
                    additional_domain += [('date_order', '>=', start_str), ('date_order', '<=', end_str)]

            full_domain = base_domain + additional_domain
            rec.model_domain = repr(full_domain)
            
    
    @api.onchange('model_domain')
    def _onchange_model_domain(self):
        for rec in self:
            if not rec.model_domain or not rec.performance_id or not rec.model_id:
                continue
            try:
                domain = ast.literal_eval(rec.model_domain)
            except Exception:
                raise UserError("Invalid domain format. Please use a proper domain syntax.")

            model = rec.model_id.model
            emp = rec.performance_id.employee_id
            user_id_condition_valid = False

            # Check based on model type
            if model in ['account.move', 'crm.lead', 'sale.order', 'mail.activity']:
                for condition in domain:
                    if isinstance(condition, (list, tuple)) and len(condition) == 3:
                        field, operator, value = condition
                        if field == 'user_id' and operator == '=' and value == emp.id:
                            user_id_condition_valid = True
                            break
                if not user_id_condition_valid:
                    # Reset to correct user_id domain
                    rec.model_domain = str([('user_id', '=', emp.id)])
                    raise UserError("You cannot remove or change the assigned employee (user_id). Domain has been reset.")

            elif model == 'project.task':
                for condition in domain:
                    if isinstance(condition, (list, tuple)) and len(condition) == 3:
                        field, operator, value = condition
                        if field == 'user_ids' and operator == 'in' and value == emp.id:
                            user_id_condition_valid = True
                            break
                if not user_id_condition_valid:
                    # Reset to correct user_ids domain
                    rec.model_domain = str([('user_ids', 'in', emp.id)])
                    raise UserError("You cannot remove or change the assigned employee (user_ids). Domain has been reset.")

            

    
    @api.depends('model_id', 'model_domain')
    def _compute_done(self):
        for rec in self:
            rec.done = 0
            if not rec.model_id or not rec.model_domain:
                continue
            try:
                domain = eval(rec.model_domain)
                model = self.env[rec.model_id.model]
                rec.done = model.search_count(domain)
            except Exception as e:
                _logger.warning(f"Failed to evaluate domain: {rec.model_domain} on model {rec.model_id.model}: {e}")
                rec.done = 0

            

    @api.depends('target', 'done')
    def _compute_percentage(self):
        for line in self:
            line.percentage = (line.done / line.target * 100) / 100 if line.target > 0 else 0.0
            




class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    model_ids = fields.Many2many(
        comodel_name='ir.model',
        string='Allowed Models for Performance',
        help="Select models allowed for performance tracking."
    )
    
    model_ids_stored = fields.Char(
        string='Stored Allowed Models',
        config_parameter='performance.allowed_model_ids'
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        stored_value = self.env['ir.config_parameter'].sudo().get_param('performance.allowed_model_ids', default='')
        if stored_value:
            model_ids = [int(id) for id in stored_value.split(',') if id]
            res['model_ids'] = [(6, 0, model_ids)]  
        else:
            res['model_ids'] = [(5, 0, 0)]  
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.model_ids:
            stored_value = ','.join(str(id) for id in self.model_ids.ids)
        else:
            stored_value = ''
        self.env['ir.config_parameter'].sudo().set_param('performance.allowed_model_ids', stored_value)

    def get_allowed_model_ids(self):
        stored_value = self.env['ir.config_parameter'].sudo().get_param('performance.allowed_model_ids', default='')
        if stored_value:
            return [int(id) for id in stored_value.split(',') if id]
        return []