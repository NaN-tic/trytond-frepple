#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool

__all__ = ['Simulation', 'Problem']


class Simulation(ModelSQL, ModelView):
    'frePPLe Simulation'
    __name__ = 'frepple.simulation'
    name = fields.Char('Name', required=True)
    date = fields.DateTime('Date', required=True)

class Problem(ModelSQL, ModelView):
    'FrePPLe Problem'
    __name__ = 'frepple.problem'
    simulation = fields.Many2One('frepple.simulation', 'Simulation',
        required=True)
    name = fields.Char('Name')
    entity = fields.Char('Entity')
    description = fields.Char('Description')
    start = fields.DateTime('Start')
    end = fields.DateTime('End')
    weight = fields.Float('Weight')
