import os
import sys
import atexit
from ctypes import *
from tempfile import NamedTemporaryFile

from . import imports, device
from . import cothread_dispatcher

__all__ = ['dbLoadDatabase', 'iocInit', 'interactive_ioc']


# tie in epicsAtExit() to interpreter lifecycle
@atexit.register
def epicsAtPyExit():
    imports.epicsExitCallAtExits()


def iocInit(dispatcher=None):
    '''This must be called exactly once after loading all EPICS database files.
    After this point the EPICS IOC is running and serving PVs.

    Args:
        dispatcher: A callable with signature ``dispatcher(func, *args)``. Will
            be called in response to caput on a record. If not supplied use
            `cothread` as a dispatcher.

    See Also:
        `softioc.asyncio_dispatcher` is a dispatcher for `asyncio` applications
    '''
    if dispatcher is None:
        # Fallback to cothread
        dispatcher = cothread_dispatcher.CothreadDispatcher()
    # Set the dispatcher for record processing callbacks
    device.dispatcher = dispatcher
    imports.iocInit()


def safeEpicsExit(code=0):
    '''Calls epicsExit() after ensuring Python exit handlers called.'''
    if hasattr(sys, 'exitfunc'):  # py 2.x
        try:
            # Calling epicsExit() will bypass any atexit exit handlers, so call
            # them explicitly now.
            sys.exitfunc()
        finally:
            # Make sure we don't try the exit handlers more than once!
            del sys.exitfunc

    elif hasattr(atexit, '_run_exitfuncs'):  # py 3.x
        atexit._run_exitfuncs()

    # calls epicsExitCallAtExits()
    # and then OS exit()
    imports.epicsExit(code)
epicsExit = safeEpicsExit

# The following identifiers will be exported to interactive shell.
command_names = []


# IOC Test facilities
def ExportTest(name, argtypes, defaults=(), description='no description yet',
               lib=imports.dbCore):
    f = getattr(lib, name)
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


ExportTest('dba', (auto_encode,), (), '''\
dba(field)

Prints value of each field in dbAddr structure associated with field.''')

ExportTest('dbl', (auto_encode, auto_encode,), ('', ''), '''\
dbl(pattern='', fields='')

Prints the names of records in the database matching pattern.  If a (space
separated) list of fields is also given then the values of the fields are also
printed.''')

ExportTest('dbnr', (c_int,), (0,), '''\
dbnr(all=0)

Print number of records of each record type.''')

ExportTest('dbgrep', (auto_encode,), (), '''\
dbgrep(pattern)

Lists all record names that match the pattern. * matches any number of
characters in a record name.''')

ExportTest('dbgf', (auto_encode,), (), '''\
dbgf(field)

Prints field type and value.''')

ExportTest('dbpf', (auto_encode, auto_encode,), (), '''\
dbpf(field, value)

Writes the given value into the field.''')

ExportTest('dbpr', (auto_encode, c_int,), (0,), '''\
dbpr(record, interest=0)

Prints all the fields in record up to the indicated interest level:

= ========================================================
0 Application fields which change during record processing
1 Application fields which are fixed during processing
2 System developer fields of major interest
3 System developer fields of minor interest
4 All other fields
= ========================================================''')

ExportTest('dbtr', (auto_encode,), (), '''\
dbtr(record)

Tests processing of the specified record.''')

ExportTest('dbtgf', (auto_encode,), (), '''\
dbtgf(field_name)

This performs a dbNameToAddr and then calls dbGetField with all possible request
types and options. It prints the results of each call. This routine is of most
interest to system developers for testing database access.''')

ExportTest('dbtpf', (auto_encode, auto_encode,), (), '''\
dbtpf(field_name, value)

This command performs a dbNameToAddr, then calls dbPutField, followed by dbgf
for each possible request type. This routine is of interest to system developers
for testing database access.''')

ExportTest('dbtpn', (auto_encode, auto_encode,), (), '''\
dbtpn(field, value)

This command performs a dbProcessNotify request. If a non-null value argument
string is provided it issues a putProcessRequest to the named record; if no
value is provided it issues a processGetRequest. This routine is mainly of
interest to system developers for testing database access.''')

ExportTest('dbior', (auto_encode, c_int,), ('', 0,), '''\
dbior(driver='', interest=0)

Prints driver reports for the selected driver (or all drivers if driver is
omitted) at the given interest level.''')

ExportTest('dbhcr', (), (), '''\
dbhcr()

Prints hardware configuration report.''')

ExportTest('gft', (auto_encode,), (), '''\
gft(field)

Get Field Test for old database access''')

ExportTest('pft', (auto_encode,), (), '''\
pft(field, value)

Put Field Test for old database access''')

ExportTest('tpn', (auto_encode, auto_encode,), (), '''\
tpn(field, value)

Test Process Notify for old database access''')

ExportTest('dblsr', (auto_encode, c_int,), (), '''\
dblsr(recordname, level)

This command generates a report showing the lock set to which each record
belongs. If recordname is 0, "", or "*" all records are shown, otherwise only
records in the same lock set as recordname are shown.

level can have the following values:

= =======================================================
0 Show lock set information only
1 Show each record in the lock set
2 Show each record and all database links in the lock set
= =======================================================''')

ExportTest('dbLockShowLocked', (c_int,), (), '''\
dbLockShowLocked(level)

This command generates a report showing all locked locksets, the records they
contain, the lockset state and the thread that currently owns the lockset. The
level argument is passed to epicsMutexShow to adjust the information reported
about each locked epicsMutex.''')

ExportTest('scanppl', (c_double,), (0.0,), '''\
scanppl(rate=0.0)

Prints all records with the selected scan rate (or all if rate=0).''')

ExportTest('scanpel', (c_int,), (0,), '''\
scanpel(event=0)

Prints all records with selected event number (or all if event=0).''')

ExportTest('scanpiol', (), (), '''\
scanpiol()

Prints all records in the I/O event scan lists.''')

ExportTest('generalTimeReport', (c_int,), (0,), '''\
generalTimeReport(int level)

This routine displays the time providers and their priority levels that have
registered with the General Time subsystem for both current and event times. At
level 1 it also shows the current time as obtained from each provider.''',
           lib=imports.Com)

ExportTest('eltc', (c_int,), (), '''\
eltc(noYes)

This determines if error messages are displayed on the IOC console. 0 means no
and any other value means yes.''',
           lib=imports.Com)


# Hacked up exit object so that when soft IOC framework sends us an exit command
# we actually exit.
class Exiter:
    def __repr__(self):  # hack to exit when "called" with no parenthesis
        sys.exit(0)
    def __call__(self, code=0):
        sys.exit(code)

exit = Exiter()
command_names.append('exit')


def dbLoadDatabase(database, path = None, substitutions = None):
    '''Loads a database file and applies any given substitutions.'''
    imports.dbLoadDatabase(database, path, substitutions)


def _add_records_from_file(dirname, file, substitutions):
    # This is very naive, it loads all includes before their parents which
    # possibly can put them out of order, but it works well enough for
    # devIocStats
    with open(os.path.join(dirname, file)) as f:
        lines, include_subs = [], ''
        for line in f.readlines():
            line = line.rstrip()
            if line.startswith('substitute'):
                # substitute "QUEUE=scanOnce, QUEUE_CAPS=SCANONCE"
                # keep hold of the substitutions
                include_subs = line.split('"')[1]
            elif line.startswith('include'):
                # include "iocQueue.db"
                subs = substitutions
                if substitutions and include_subs:
                    subs = substitutions + ', ' + include_subs
                else:
                    subs = substitutions + include_subs
                _add_records_from_file(dirname, line.split('"')[1], subs)
            else:
                # A record line
                lines.append(line)
        # Write a tempfile and load it
        with NamedTemporaryFile(suffix='.db', delete=False) as f:
            f.write(os.linesep.join(lines).encode())
        dbLoadDatabase(f.name, substitutions=substitutions)
        os.unlink(f.name)


def devIocStats(ioc_name):
    '''This will load a template for the devIocStats library with the specified
    IOC name. This should be called before `iocInit`'''
    substitutions = 'IOCNAME=' + ioc_name + ', TODFORMAT=%m/%d/%Y %H:%M:%S'
    iocstats_dir = os.path.join(
        os.path.dirname(__file__), 'iocStats', 'iocAdmin', 'Db')
    _add_records_from_file(iocstats_dir, 'ioc.template', substitutions)


def interactive_ioc(context = {}, call_exit = True):
    '''Fires up the interactive IOC prompt with the given context.

    Args:
        context: A dictionary of values that will be made available to the
            interactive Python shell together with a number of EPICS test
            functions
        call_exit: If `True`, the IOC will be terminated by calling epicsExit
            which means that `interactive_ioc` will not return
    '''
    # Add all our commands to the given context.
    exports = dict((key, globals()[key]) for key in command_names)
    import code

    try:
        code.interact(local = dict(exports, **context), exitmsg = '')
    except SystemExit as e:
        if call_exit:
            safeEpicsExit(e.code)
        raise

    if call_exit:
        safeEpicsExit(0)
