#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.pool import Pool
from .frepple import *

def register():
    Pool.register(
        Simulation,
        Problem,
	LaunchFrePPLeStart,
        module='frepple', type_='model')
    Pool.register(
	LaunchFrePPLe,
        module='frepple', type_='wizard')
