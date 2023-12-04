
from odoo import api, fields, models

class ResCompany(models.Model):
    
    _inherit = "res.company"
    
    sales_goal = fields.Float(
        string='Sales Goal',
        store=True,
        help='Transactional sales goal',
        tracking=True,
    )
