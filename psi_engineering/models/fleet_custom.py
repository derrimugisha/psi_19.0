# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from datetime import datetime

class FleetVehicle(models.Model):
    
    _inherit ="fleet.vehicle"
    