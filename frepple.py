#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
import subprocess
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateAction, StateView, StateTransition, \
    Button
from trytond.pool import Pool
from trytond.rpc import RPC

__all__ = ['Simulation', 'Problem', 'LaunchFrePPLeStart', 'LaunchFrePPLe']


def check_output(*args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    process.wait()
    data = process.stdout.read()
    return data


def execute_frepple():
    import os
    cwd = os.getcwd()
    os.chdir('/home/albert/tmp/frepple-2.0/bin')
    print check_output('./run')


class Simulation(ModelSQL, ModelView):
    'frePPLe Simulation'
    __name__ = 'frepple.simulation'
    name = fields.Char('Name', required=True)
    date = fields.DateTime('Date', required=True)

    @classmethod
    def __setup__(cls):
        super(Simulation, cls).__setup__()
        cls.__rpc__.update({
                'execute': RPC(readonly=False),
                })

    @classmethod
    def process(cls, simulations):
        execute_frepple()


class Problem(ModelSQL, ModelView):
    'FrePPLe Problem'
    __name__ = 'frepple.problem'
    _order = [
        ('simulation', 'ASC'),
        ('weight', 'DESC'),
        ]
    simulation = fields.Many2One('frepple.simulation', 'Simulation',
        required=True)
    name = fields.Char('Name')
    entity = fields.Char('Entity')
    description = fields.Char('Description')
    start = fields.DateTime('Start')
    end = fields.DateTime('End')
    weight = fields.Float('Weight')


class LaunchFrePPLeStart(ModelView):
    'Launch frePPLe'
    __name__ = 'frepple.launch_frepple.start'
    plan = fields.Selection([
            ('constrained', 'Constrained'),
            ('unconstrained', 'Unconstrained'),
            ], 'Plan', required=True)
    capacity = fields.Boolean('Respect capacity limits')
    material = fields.Boolean('Respect procurement limits')
    lead_time = fields.Boolean('Do not plan in the past')
    release_fence = fields.Boolean('Do not plan within the release time window')

    @staticmethod
    def default_plan():
        return 'constrained'

    @staticmethod
    def default_capacity():
        return True

    @staticmethod
    def default_material():
        return True

    @staticmethod
    def default_lead_time():
        return True

    @staticmethod
    def default_release_fence():
        return True


class LaunchFrePPLe(Wizard):
    'Launch frePPLe'
    __name__ = 'frepple.launch_frepple'
    start = StateView('frepple.launch_frepple.start',
        'frepple.launch_frepple_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Launch', 'launch', 'tryton-ok', default=True),
            ])
    launch = StateAction('frepple.act_frepple_simulation')

    def do_launch(self, action):
        execute_frepple()
        return action, {}
