'''Top level import script for soft IOC support.'''

import os
import sys
from ctypes import *

from . import imports

__all__ = ['dbLoadDatabase', 'iocInit', 'interactive_ioc']


iocInit = imports.iocInit
epicsExit = imports.epicsExit

def safeEpicsExit():
    '''Calls epicsExit() after ensuring Python exit handlers called.'''
    if hasattr(sys, 'exitfunc'):
        try:
            # Calling epicsExit() will bypass any atexit exit handlers, so call
            # them explicitly now.
            sys.exitfunc()
        finally:
            # Make sure we don't try the exit handlers more than once!
            del sys.exitfunc
    epicsExit()


# The following identifiers will be exported to interactive shell.
command_names = []


# IOC Test facilities
def ExportTest(name, argtypes, defaults=(), description='no description yet'):
    f = getattr(imports.libdbIoc, name)
    f.argtypes = argtypes
    f.restype = None

    length = len(argtypes)
    def call_f(*args):
        missing = length - len(args)
        if missing > 0:
            # Add in the missing arguments from the given defaults
            args = args + defaults[-missing:]
        f(*args)

    call_f.__doc__ = description
    call_f.__name__ = name
    globals()[name] = call_f
    command_names.append(name)


auto_encode = imports.auto_encode


ExportTest('dba', (auto_encode,), (),
    '''dba(field)

    Prints value of each field in dbAddr structure associated with field.''')

ExportTest('dbl', (auto_encode, auto_encode,), ('', ''),
    '''dbl(pattern='', fields='')

    Prints the names of records in the database matching pattern.  If
    a (space separated) list of fields is also given then the values of
    the fields are also printed.''')

ExportTest('dbnr', (c_int,), (0,),
    '''dbnr(all=0)

    Print number of records of each record type.''')

ExportTest('dbgrep', (auto_encode,), (),
    '''dbgrep(pattern)

    Lists all record names that match the pattern.  * matches any number of
    characters in a record name.''')

ExportTest('dbgf', (auto_encode,), (),
    '''dbgf(field)

    Prints field type and value.''')

ExportTest('dbpf', (auto_encode, auto_encode,), (),
    '''dbpf(field, value)

    Writes the given value into the field.''')

ExportTest('dbpr', (auto_encode, c_int,), (0,),
    '''dbpr(record, interest=0)

    Prints all the fields in record up to the indicated interest level:

    0 Application fields which change during record processing
    1 Application fields which are fixed during processing
    2 System developer fields of major interest
    3 System developer fields of minor interest
    4 All other fields.''')

ExportTest('dbtr', (auto_encode,), (),
    '''dbtr(record)

    Tests processing of the specified record.''')

ExportTest('dbtgf', (auto_encode,))
ExportTest('dbtpf', (auto_encode, auto_encode,))

ExportTest('dbior', (auto_encode, c_int,), ('', 0,),
    '''dbior(driver='', interest=0)

    Prints driver reports for the selected driver (or all drivers if
    driver is omitted) at the given interest level.''')

ExportTest('dbhcr', (), (), '''Prints hardware configuration report.''')

ExportTest('gft', (auto_encode,))
ExportTest('pft', (auto_encode,))
ExportTest('dbtpn', (auto_encode, auto_encode,))
ExportTest('tpn', (auto_encode, auto_encode,))
ExportTest('dblsr', (auto_encode, c_int,))
ExportTest('dbLockShowLocked', (c_int,))

ExportTest('scanppl', (c_double,), (0.0,),
    '''scanppl(rate=0.0)

    Prints all records with the selected scan rate (or all if rate=0).''')

ExportTest('scanpel', (c_int,), (0,),
    '''scanpel(event=0)

    Prints all records with selected event number (or all if event=0).''')

ExportTest('scanpiol', (), (),
    '''Prints all records in the I/O event scan lists.''')

ExportTest('generalTimeReport', (c_int,), (0,),
    '''Displays time providers and their status''')

ExportTest('eltc', (c_int,), (),
    '''Turn EPICS logging on or off.''')


# Hacked up exit object so that when soft IOC framework sends us an exit command
# we actually exit.
class Exiter:
    def __repr__(self):
        safeEpicsExit()
    def __call__(self):
        safeEpicsExit()

exit = Exiter()
command_names.append('exit')


def dbLoadDatabase(database, path = None, substitutions = None):
    '''Loads a database file and applies any given substitutions.'''
    imports.dbLoadDatabase(database, path, substitutions)

def devIocStats(ioc_name):
    dbLoadDatabase(
        'ioc.db', os.path.join(os.getenv('HERE'), 'db'),
        'IOCNAME=%s,name=' % ioc_name)


def interactive_ioc(context = {}, call_exit = True):
    '''Fires up the interactive IOC prompt with the given context.'''
    # Add all our commands to the given context.
    exports = dict((key, globals()[key]) for key in command_names)
    import code

    if sys.version_info < (3, 6):
        interact_args = {}
    else:
        # This suppresses irritating exit message introduced by Python3.  Alas,
        # this option is only available in Python 3.6!
        interact_args = dict(exitmsg = '')
    code.interact(local = dict(exports, **context), **interact_args)

    if call_exit:
        safeEpicsExit()
