from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class Agenda(models.Model):
    _name = 'gms.agenda'
    _description = 'Agenda'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    name = fields.Char(
    'Name', )


    name = fields.Char(required=True, default=lambda self: _('New'), copy=False, readonly=True, tracking=True)
    fecha = fields.Date(string='Fecha', required=True, tracking="1", default=fields.Date.today())
    fecha_viaje = fields.Date(string='Fecha de viaje', required=True, tracking="1")
    origen = fields.Many2one('res.partner', string='Origen', required=True, tracking="1", domain="['&',('tipo', '!=', False),('parent_id','=',solicitante_id)]")
    destino = fields.Many2one('res.partner', string='Destino', required=True, tracking="1", domain="[('tipo', '!=', False)]")
    transportista_id = fields.Many2one('res.partner', string='Trasportista', readonly=True, states={'cancelado': [('readonly', True)]}, tracking="1")
    camion_disponible_id = fields.Many2one('gms.camiones.disponibilidad',
                                           string='Disponibilidad Camión',
                                           states={'cancelado': [('readonly', True)]},
                                           tracking="1",
                                           domain="[('estado', '=', 'disponible'), ('camion_id.disponible_zafra', '=', True)]",
                                           attrs="{'invisible': [('state', '=', 'solicitud')]}")  # Ocultar en solicitud

    camion_id = fields.Many2one('gms.camiones', string='Camion', readonly=True)
    conductor_id = fields.Many2one('res.partner', string='Chofer', readonly=True)
    solicitante_id = fields.Many2one('res.partner', string='Solicitante', required=True, tracking="1", domain="[('tipo', '=', False)]")

    viaje_count = fields.Integer(string="Número de viajes", compute="_compute_viaje_count")
    tipo_viaje = fields.Selection([('entrada', 'Entrada'), ('salida', 'Salida')], string="Tipo de Viaje")

    


    @api.depends('name') 
    def _compute_viaje_count(self):
        for record in self:
            record.viaje_count = self.env['gms.viaje'].search_count([('agenda', '=', record.id)])



    state = fields.Selection([
        ('solicitud', 'Solicitud'),
        ('proceso', 'Proceso'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado')
    ], string='Estado', default='solicitud', required=True)

    follower_ids = fields.Many2many('res.users', string='Followers')

    @api.onchange('camion_disponible_id')
    def _onchange_camion_disponible_id(self):
        if self.camion_disponible_id:
            self.transportista_id = self.camion_disponible_id.transportista_id.id
            self.conductor_id = self.camion_disponible_id.conductor_id.id
            self.camion_id = self.camion_disponible_id.camion_id.id
            

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('gms.agenda')
        return super().create(vals_list)

    def action_cancel(self):
        self.write({'state': 'cancelado'})

    def action_proceso(self):
        self.write({'state': 'proceso'})

    def action_view_scheduled_trips(self):
        self.ensure_one()  # Asegura que solo se está trabajando con un registro a la vez
        viaje = self.env['gms.viaje'].search([('agenda', '=', self.id)], limit=1)
        if viaje:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'gms.viaje',
                'view_mode': 'form',
                'res_id': viaje.id,
                'target': 'current',
            }
        else:
            raise UserError(_('No hay un viaje asociado a esta agenda.'))   

    def _check_fecha_viaje(self):
        for agenda in self:
            if agenda.fecha_viaje:
                fecha_viaje = fields.Date.from_string(agenda.fecha_viaje)
                fecha_actual = fields.Date.from_string(fields.Date.today())
                dias_diferencia = (fecha_viaje - fecha_actual).days
                if dias_diferencia > 1:
                    raise UserError("No se puede confirmar: La fecha de viaje es mayor a 1 día desde la fecha actual.")

    def action_confirm(self):
       
        self._check_fecha_viaje()
        
        if self.camion_disponible_id:
            self.camion_disponible_id.write({'estado': 'ocupado'})

        viaje = self.env['gms.viaje'].create({
            'agenda': self.id,
            'fecha_viaje': self.fecha_viaje,
            'origen': self.origen.id,
            'destino': self.destino.id,
            'camion_disponible_id': self.camion_disponible_id.id,
            'camion_id': self.camion_disponible_id.camion_id.id,  
            'conductor_id': self.camion_disponible_id.conductor_id.id,
            'solicitante_id': self.solicitante_id.id,
            'tipo_viaje': self.tipo_viaje,
            'transportista_id': self.transportista_id.id,    
            'state': 'proceso'
            
            
            
        })

        if self.camion_disponible_id:
            self.env['gms.historial'].create({
                'fecha': self.fecha,
                'camion_id': self.camion_disponible_id.camion_id.id,
                'agenda_id': self.id,
            })

        self.write({'state': 'confirmado'})



    def unlink(self):
        for record in self:
            if record.state in ['proceso', 'confirmado', 'cancelado']:
                raise UserError(_('No puedes eliminar una agenda en el estado %s.') % record.state)
        return super(Agenda, self).unlink()