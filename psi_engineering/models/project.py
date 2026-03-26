from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
class ProjectType(models.Model):
    _name = 'project.type'
    _description = 'Project Type'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Project Type Name", tracking=True)
    milestone_template_ids = fields.One2many('project.milestone.template', 'project_type_id', string="Milestone Templates")
class ProjectProject(models.Model):
    _inherit ="project.project"
    
    project_type_id = fields.Many2one('project.type', string="Project Type")
    
    milestone_count = fields.Integer(string="Milestone Count", compute="_compute_milestone_count")

    def _compute_milestone_count(self):
        for project in self:
            project.milestone_count = self.env['project.milestone'].search_count([('project_id', '=', project.id)])

    def action_view_milestones(self):
        """This method returns an action that displays the milestones related to this project."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Milestones',
            'res_model': 'project.milestone',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
        }
    
    def action_add_milestone(self):
        """This method will create a new milestone for the project."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Milestone',
            'res_model': 'project.milestone',
            'view_mode': 'form',
            'view_id': self.env.ref('project.project_milestone_view_form').id,
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_project_type_id': self.project_type_id.id if self.project_type_id else False
            },
        }
class ProjectMilestoneTemplate(models.Model):
    _name = 'project.milestone.template'
    _description = 'Project Milestone Template'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Milestone Template Name", tracking=True)
    project_type_id = fields.Many2one('project.type', string="Project Type", ondelete='cascade', tracking=True)
    milestone_item_ids = fields.One2many('project.milestone.item', 'milestone_template_id', string="Milestone Items")

class ProjectMilestoneItem(models.Model):
    _name = 'project.milestone.item'
    _description = 'Milestone Item'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, string="Question/Name", tracking=True)
    no = fields.Char()
    milestone_template_id = fields.Many2one('project.milestone.template', string="Milestone Template", ondelete='cascade', tracking=True)
    answer_type = fields.Selection([
        ('pass_fail', 'Pass/Fail'),
        ('number', 'Number'),
        ('text', 'Text')
    ], string="Answer Type",  tracking=True)
    answer_pass_fail = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string="Pass/Fail", tracking=True)
    answer_number = fields.Float(string="Number", tracking=True)
    answer_text = fields.Text(string="Text", tracking=True)
    comments = fields.Text(string="Comments", tracking=True)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note')
    ], string="Display Type", tracking=True, help="Used for separating lines visually in the UI. No effect on processing.")

class ProjectMilestone(models.Model):
    _name ="project.milestone"
    _inherit = ['mail.thread','project.milestone']
    
    user_id = fields.Many2one('res.users', tracking=True)
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
        'milestone_id', 
        string="Checklists"
    )
    
    image_ids = fields.One2many(
        'project.milestone.images', 
        'milestone_id', 
        string="Milestone Images"
    )
    
    attachment_ids = fields.Many2many('ir.attachment', string="Milestone Attachments")
    checklist_completed = fields.Boolean("Check list Completed",tracking=True,)
    checklist_completed_by = fields.Many2one("res.users", string="Checklist Completed By",tracking=True,)
    receipt_printed = fields.Boolean(string="Receipt Printed", default=False)
    

    # Define the states
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string="State", default='draft', tracking=True)

    # Actions to change states
    def action_start(self):
        """Set the milestone state to 'In Progress'."""
        self.state = 'in_progress'

    def action_complete(self):
        """Set the milestone state to 'Completed'."""
        if self.milestone_template_id:
            if len(self.checklist_ids.filtered(lambda x: not x.display_type and x.answer_type == 'pass_fail' and not x.answer_pass_fail)) > 0:
                raise UserError('Please first Complete the Check List before Completing the Milestone')
            if len(self.checklist_ids.filtered(lambda x: not x.display_type and x.answer_type == 'number' and x.answer_number == 0)) > 0:
                raise UserError('Please first Complete the Check List before Completing the Milestone')
            if len(self.checklist_ids.filtered(lambda x: not x.display_type and x.answer_type == 'text' and not x.answer_text)) > 0:
                raise UserError('Please first Complete the Check List before Completing the Milestone')
        self.state = 'completed'
        self.is_reached = True


    def action_reset_to_draft(self):
        """Reset the milestone state to 'Draft'."""
        self.state = 'draft'


    @api.onchange('milestone_template_id')
    def _onchange_milestone_template_id(self):
        if self.milestone_template_id:
            self.checklist_ids = [(5,0,0)]
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
            self.checklist_ids = [(5,0,0)]
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
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        website_url = f"{base_url}/milestone/checklist/{self.id}"  # Assuming the milestone form URL includes project id

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
            'res_id':self.id,
            'context': {
                'default_project_id': self.project_id.id,
                'default_project_type_id': self.project_type_id.id if self.project_type_id else False
            },
        }

    def print_milestone_report(self):
        for record in self:
            if not record.receipt_printed:
                record.receipt_printed = True
                return self.env.ref('psi_engineering.action_print_milestone_report').report_action(record)
            else:
                raise UserError('Milestone report already printed.')

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("Creating milestones: %s", vals_list)
        milestones = super(ProjectMilestone, self).create(vals_list)
        for milestone in milestones:
            if milestone.milestone_template_id:
                checklist_items = []
                for item in milestone.milestone_template_id.milestone_item_ids:
                    checklist_items.append((0, 0, {
                        'no': item.no,
                        'name': item.name,
                        'display_type': item.display_type,
                        'answer_type': item.answer_type,
                        'comments': item.comments or '',
                        'milestone_template_id': milestone.milestone_template_id.id,
                        'project_id': milestone.project_id.id if milestone.project_id else False,
                        'project_type_id': milestone.project_type_id.id if milestone.project_type_id else False,
                    }))
                milestone.checklist_ids = checklist_items
                _logger.info("Checklist items added for milestone ID %s: %s", milestone.id, checklist_items)
        return milestones


class ProjectMilestoneChecklist(models.Model):
    _name = 'project.milestone.checklist'
    _inherit =['mail.thread','mail.activity.mixin']
    _description = 'Project Milestone Checklist'
    
    project_id = fields.Many2one('project.project', string="Project", required=True)
    milestone_id = fields.Many2one('project.milestone', string="Milestone", )
    task_id = fields.Many2one('project.task', string="Task",)
    # milestone_template_id = fields.Many2one('project.milestone.template', string="Milestone Template", required=True)
    milestone_template_id = fields.Many2one('project.milestone.template', string="Milestone Template")
    name = fields.Char(string="Name/Question", required=True)
    no = fields.Float("No", tracking=True)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
        ('line_item', 'Item')
    ], string="Display Type", help="Used to distinguish between sections, notes, and items.", default='line_item')
    project_type_id = fields.Many2one('project.type', string="Project Type", )
    
    answer_type = fields.Selection([
        ('pass_fail', 'Pass/Fail'),
        ('number', 'Number'),
        ('text', 'Text')
    ], string="Answer Type", )

    answer_pass_fail = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string="Pass/Fail")
    
    answer_number = fields.Float(string="Number")
    
    answer_text = fields.Text(string="Text")
    
    comments = fields.Text(string="Comments")
    
    remarks = fields.Text(string="Remarks")

class ProjectMilestoneImages(models.Model):
    _name = 'project.milestone.images'
    _description = 'Project Milestone Images'

    name = fields.Char(string="Name", required=True)
    milestone_id = fields.Many2one('project.milestone', string="Milestone", )
    project_id = fields.Many2one('project.project', string="Project", required=True)
    project_type_id = fields.Many2one('project.type', string="Project Type", required=True)
    image = fields.Binary(string="Image", required=True)
    task_id = fields.Many2one("project.task", string="Task")
    
