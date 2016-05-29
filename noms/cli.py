"""
Command-line interface for noms
"""

import mongoengine

from twisted.web import tap

from noms.server import Server
from noms import config, CONFIG

MAIN_FUNC = 'noms.cli.main'


class NomsOptions(tap.Options):
    optParameters = tap.Options.optParameters + [
            ['db', None, 'noms', 'Database name or connect string'],
            ]

    def postOptions(self):
        mongoengine.connect(db=self['db'])
        CONFIG.load()

        # now we know CONFIG exists
        CONFIG.cliOptions = dict(self.items())
        CONFIG.save()

        self.opt_class(MAIN_FUNC)

        return tap.Options.postOptions(self)


Options = NomsOptions


makeService = tap.makeService


def main():
    """
    Return a resource to start our application
    """
    resource = Server().app.resource
    mongoengine.connect(db=CONFIG.cliOptions['db'])
    return resource()
