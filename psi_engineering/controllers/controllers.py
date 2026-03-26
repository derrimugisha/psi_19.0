# -*- coding: utf-8 -*-
# from odoo import http

from odoo import http
from odoo.http import request
import base64

class MilestoneChecklistController(http.Controller):
    
    @http.route(['/milestone/checklist/completed'], type='http', auth='public', website=True)
    def milestone_checklist_completed(self,  **kwargs):
        return request.render('psi_engineering.milestone_checklist_completed')

    @http.route(['/milestone/checklist/thank_you'], type='http', auth='public', website=True)
    def milestone_checklist_thank_you(self,  **kwargs):
        return request.render('psi_engineering.milestone_checklist_thank_you')

    @http.route(['/milestone/checklist/<int:milestone_id>'], type='http', auth='public', website=True)
    def milestone_checklist_form(self, milestone_id, **kwargs):
        milestone = request.env['project.milestone'].sudo().browse(milestone_id)
        if not milestone:
            return request.not_found()
        if milestone.checklist_completed:
            return request.redirect('/milestone/checklist/thank_you')

        return request.render('psi_engineering.milestone_checklist_template', {
            'milestone': milestone,
        })

    @http.route(['/milestone/checklist/submit'], type='http', auth='public', methods=['POST'], website=True)
    def milestone_checklist_submit(self, **post):
        milestone_id = int(post.get('milestone_id'))
        milestone = request.env['project.milestone'].sudo().browse(milestone_id)

        if not milestone:
            return request.not_found()

        for checklist in milestone.checklist_ids:
            answer_key = 'answer_%d' % checklist.id
            if checklist.answer_type == 'pass_fail':
                checklist.sudo().write({'answer_pass_fail': post.get(answer_key)})
            elif checklist.answer_type == 'number':
                checklist.sudo().write({'answer_number': float(post.get(answer_key, 0))})
            elif checklist.answer_type == 'text':
                checklist.sudo().write({'answer_text': post.get(answer_key)})
                
         # Handle image uploads and descriptions
        image_count = 1
        while f'image_file_{image_count}' in request.httprequest.files:
            image_file = request.httprequest.files[f'image_file_{image_count}']
            image_description = post.get(f'image_description_{image_count}', '')

            # Convert the image to binary data for storing in the database
            image_data = image_file.read()
            if image_data:
                # Ensure the image is Base64 encoded
                encoded_image_data = base64.b64encode(image_data)

                # Create a new milestone image record
                request.env['project.milestone.images'].sudo().create({
                    'milestone_id': milestone.id,
                    'project_id': milestone.project_id.id,
                    'project_type_id': milestone.project_type_id.id,
                    'name': image_description or f"Image {image_count}",
                    'image': encoded_image_data,
                })

            else:
                _logger.error(f"No data found in image_file_{image_count}")    
            image_count += 1
            
        
        milestone.checklist_completed = True
        milestone.checklist_completed_by = request.env.user.id

        return request.redirect('/milestone/checklist/thank_you')

