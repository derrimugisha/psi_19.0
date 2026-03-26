from odoo import fields, models, api, _

class Bid(models.Model):
    _inherit ='bid'

    lead_id = fields.Many2one('crm.lead', string="Related Lead", readonly=True)

    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
            'target': 'current',
        }