'''Top level import script for soft IOC support.'''

from ctypes import *

import imports
import cothread

__all__ = ['dbLoadDatabase', 'iocInit', 'interactive_ioc']

iocInit = imports.iocInit


# IOC Test facilities
def ExportTest(name, argtypes, defaults=(), description='not yet'):
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
    __all__.append(name)

    
ExportTest('dba', (c_char_p,), (),
    '''dba(field)

    Prints value of each field in dbAddr structure associated with field.''')
    
ExportTest('dbl', (c_char_p, c_char_p,), ('', ''),
    '''dbl(pattern='', fields='')

    Prints the names of records in the database matching pattern.  If
    a (space separated) list of fields is also given then the values of
    the fields are also printed.''')
    
ExportTest('dbnr', (c_int,), (0,),
    '''dbnr(all=0)

    Print number of records of each record type.''')
    
ExportTest('dbgrep', (c_char_p,), (),
    '''dbgrep(pattern)

    Lists all record names that match the pattern.  * matches any number of
    characters in a record name.''')
    
ExportTest('dbgf', (c_char_p,), (),
    '''dbgf(field)

    Prints field type and value.''')
    
ExportTest('dbpf', (c_char_p, c_char_p,), (),
    '''dbpf(field, value)

    Writes the given value into the field.''')

ExportTest('dbpr', (c_char_p, c_int,), (0,),
    '''dbpr(record, interest=2)

    Prints all the fields in record up to the indicated interest level:

    0 Application fields which change during record processing
    1 Application fields which are fixed during processing
    2 System developer fields of major interest
    3 System developer fields of minor interest
    4 All other fields.''')
    
ExportTest('dbtr', (c_char_p,), (),
    '''dbtr(record)

    Tests processing of the specified record.''')

ExportTest('dbtgf', (c_char_p,))
ExportTest('dbtpf', (c_char_p, c_char_p,))

ExportTest('dbior', (c_char_p, c_int,), ('', 0,),
    '''dbior(driver='', interest=0)

    Prints driver reports for the selected driver (or all drivers if
    driver is omitted) at the given interest level.''')
    
ExportTest('dbhcr', (), (), '''Prints hardware configuration report.''')

ExportTest('gft', (c_char_p,))
ExportTest('pft', (c_char_p,))
ExportTest('dbtpn', (c_char_p, c_char_p,))
ExportTest('tpn', (c_char_p, c_char_p,))
ExportTest('dblsr', (c_char_p, c_int,))
ExportTest('dbLockShowLocked', (c_int,))

ExportTest('scanppl', (c_double,), (0.0,),
    '''scanppl(rate=0.0)

    Prints all records with the selected scan rate (or all if rate=0).''')

ExportTest('scanpel', (c_int,), (0,),
    '''scanpel(event=0)

    Prints all records with selected event number (or all if event=0).''')

ExportTest('scanpiol', (), (),
    '''Prints all records in the I/O event scan lists.''')




def dbLoadDatabase(database, path = None, substitutions = None):
    '''Loads a database file and applies any given substitutions.'''
    imports.dbLoadDatabase(database, path, substitutions)

    
def interactive_ioc(context = None):
    '''Fires up the interactive IOC prompt with the given set of globals.'''
    import code
    if context == None:
        context = globals()
    code.interact(local = context)
