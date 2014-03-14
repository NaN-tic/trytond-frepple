#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import ModelSingleton, ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['Configuration']


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'frePPLe Configuration'
    __name__ = 'frepple.configuration'
    path = fields.Char('Path', help='Absolute path to frepple binaries. "run" '
        'and "frepple-tryton.py" scripts should be found in that directory, as '
        'well as the "frepple" binary. Should be the "bin/" directory of the '
        'source frePPLe distribution.')
    url = fields.Char('URL', help='URL of the django-based frePPLe user '
        'interface.')

    @staticmethod
    def update_url(url):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        ActionURL = pool.get('ir.action.url')
        id = ModelData.get_id('frepple', 'act_open_frepple')
        with Transaction().set_user(0, set_context=True):
            action = ActionURL(id)
        action.url = url
        action.save()

    @classmethod
    def create(cls, vlist):
        if vlist and 'url' in vlist[0]:
            cls.update_url(vlist[0]['url'])
        return super(Configuration, cls).create(vlist)

    @classmethod
    def write(cls, configs, vals):
        super(Configuration, cls).write(configs, vals)
        if 'url' in vals:
            cls.update_url(vals['url'])
