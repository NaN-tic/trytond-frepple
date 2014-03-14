#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
import os
import json
import subprocess
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateAction, StateView, StateTransition, \
    Button
from trytond.pool import Pool
from trytond.rpc import RPC
from trytond.transaction import Transaction

__all__ = ['Simulation', 'Problem', 'LaunchFrePPLeStart', 'LaunchFrePPLe',
    'Product']


def check_output(*args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    process.wait()
    data = process.stdout.read()
    return data


class Simulation(ModelSQL, ModelView):
    'frePPLe Simulation'
    __name__ = 'frepple.simulation'
    name = fields.Char('Name', required=True)
    date = fields.DateTime('Date', required=True)
    problems = fields.One2Many('frepple.problem', 'simulation', 'Problems')

    @classmethod
    def __setup__(cls):
        super(Simulation, cls).__setup__()
        cls._order.insert(0, ('date', 'DESC'))
        cls._error_messages.update({
                'missing_configuration_path': ('frePPLe path must be '
                    'configured before executing the planner.'),
                })
        cls.__rpc__.update({
                'execute': RPC(readonly=False),
                })

    @classmethod
    def execute_frepple(cls, params):
        Configuration = Pool().get('frepple.configuration')
        config = Configuration.get_singleton()
        if not config or not config.path:
            cls.raise_user_error('missing_configuration_path')
        cwd = os.getcwd()
        script_path = os.path.abspath(__file__)
        script_path = os.path.dirname(script_path)
        script_path = os.path.join(script_path, 'frepple-tryton.py')
        ppath = os.environ.get('PYTHONPATH')
        os.environ['PYTHONPATH'] = (
            os.path.join(config.path, '../contrib/django') + (':' + ppath
                if ppath else ''))
        ld = os.environ.get('LD_LIBRARY_PATH')
        os.environ['LD_LIBRARY_PATH'] = '.' + (':' + ld if ld else '')
        params['database'] = Transaction().cursor.database_name
        os.environ['FREPPLE_TRYTON_PARAM'] = json.dumps(params)
        os.chdir(config.path)
        print check_output('./frepple', script_path)
        os.chdir(cwd)


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
        params = {
            'plan': self.start.plan,
            'capacity': self.start.capacity,
            'material': self.start.material,
            'lead_time': self.start.lead_time,
            'release_fence': self.start.release_fence,
            }
        Pool().get('frepple.simulation').execute_frepple(params)
        return action, {}


class Product(ModelSQL, ModelView):
    __name__ = 'product.product'

    @classmethod
    def __setup__(cls):
        super(Product, cls).__setup__()
        cls.__rpc__.update({
                'products_by_location': RPC(),
                })
