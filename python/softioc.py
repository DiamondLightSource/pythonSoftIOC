'''Top level import script for soft IOC support.'''

import imports
import cothread

iocInit = imports.iocInit

def dbLoadDatabase(database, path = None, substitutions = None):
    imports.dbLoadDatabase(database, path, substitutions)

def dbl(typename = None, fields = None):
    imports.dbl(typename, fields)

def interactive_ioc(globals):
    import code
    code.interact(local = globals)

    

__all__ = ['dbLoadDatabase', 'iocInit', 'dbl', 'interactive_ioc']
