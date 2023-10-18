from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    agenda_ids = fields.One2many('gms.agenda', 'order_id', string='Agendas')
    agenda_count = fields.Integer(string='Agenda Count', compute='_compute_agenda_count')

    @api.depends('agenda_ids')
    def _compute_agenda_count(self):
        for order in self:
            order.agenda_count = len(order.agenda_ids)

    def button_schedule_trip(self):

        pickings = self.env['stock.picking'].search([('origin', '=', self.name), ('picking_type_id.code', '=', 'incoming')], limit=1)

        if not pickings:
                # Aquí puedes manejar el caso en el que no se encuentra un movimiento de stock. Por ejemplo:
                raise UserError('No se encontró un movimiento de stock para esta orden de compra.')


        agenda_vals = {
            'fecha': fields.Date.today(),
            'fecha_viaje': fields.Date.today(),
            'solicitante_id': self.partner_id.id,  # Esto sería el proveedor.
            'origen': self.partner_id.id,          # Proveedor: de donde viene la mercancía.
            'destino': self.company_id.partner_id.id, # Tu empresa: a donde llegará la mercancía.
            'order_id': self.id,
            'picking_id': pickings.id,
            'tipo_viaje': 'entrada',

        }
        self.env['gms.agenda'].create(agenda_vals)
        return True

    def action_view_agenda(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agendas',
            'res_model': 'gms.agenda',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)], # Nota que esto cambió de 'picking_id' a 'order_id'
        }
