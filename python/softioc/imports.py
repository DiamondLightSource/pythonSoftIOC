'''External DLL imports used for implementing Python EPICS device support.
'''

import os
import os.path
from ctypes import *


def expect_success(status, function, args):
    assert status == 0, 'Expected success'

def expect_true(status, function, args):
    assert status, 'Expected True'


libPythonSupport = CDLL('libPythonSupport.so')

# void get_field_offsets(
#     const char * record_type, const char * field_names[], int field_count,
#     short field_offset[], short field_size[], short field_type[])
#
# Looks up field offset, size and type values for the given record type and
# the given list of field names.
get_field_offsets = libPythonSupport.get_field_offsets
get_field_offsets.argtypes = (
    c_char_p, c_void_p, c_int, c_void_p, c_void_p, c_void_p)
get_field_offsets.restype = None

# int db_put_field(const char *name, short dbrType, void *pbuffer, long length)
#
# Updates value in given field through channel access, so notifications are
# generated as appropriate.
db_put_field = libPythonSupport.db_put_field
db_put_field.argtypes = (c_char_p, c_int, c_void_p, c_long)
db_put_field.errcheck = expect_success


# char * get_EPICS_BASE()
#
# Returns the path to EPICS_BASE
get_EPICS_BASE = libPythonSupport.get_EPICS_BASE
get_EPICS_BASE.argtypes = ()
get_EPICS_BASE.restype = c_char_p


EPICS_BASE = get_EPICS_BASE()
EPICS_HOST_ARCH=os.environ['EPICS_HOST_ARCH']

def EpicsDll(dll):
    return CDLL(
        os.path.join(EPICS_BASE, 'lib', EPICS_HOST_ARCH, 'lib%s.so' % dll))


libregistryIoc = EpicsDll('registryIoc')
libdbIoc = EpicsDll('dbIoc')
libmiscIoc = EpicsDll('miscIoc')


# int registryDeviceSupportAdd(
#     const char *name,const struct dset *pdset);
#
# Registers device support.
registryDeviceSupportAdd = libregistryIoc.registryDeviceSupportAdd
registryDeviceSupportAdd.argtypes = (c_char_p, c_void_p)
registryDeviceSupportAdd.errcheck = expect_true


# void scanIoInit(IOSCANPVT *)
# void scanIoRequest(IOSCANPVT *)
#
# Initialise and trigger I/O Intr processing structure.
IOSCANPVT = c_void_p

scanIoInit = libdbIoc.scanIoInit
scanIoInit.argtypes = (IOSCANPVT,)
scanIoInit.restype = None

scanIoRequest = libdbIoc.scanIoRequest
scanIoRequest.argtypes = (IOSCANPVT,)
scanIoRequest.restype = None

dbLoadDatabase = libdbIoc.dbLoadDatabase
dbLoadDatabase.argtypes = (c_char_p, c_char_p, c_char_p)
dbLoadDatabase.errcheck = expect_success


# unsigned short recGblResetAlarms(void *precord)
#
# Raises event processing if any alarm status has changed, and resets NSTA
# and NSEV fields for further processing.
recGblResetAlarms = libdbIoc.recGblResetAlarms
recGblResetAlarms.argtypes = (c_void_p,)
recGblResetAlarms.restype = c_short


iocInit = libmiscIoc.iocInit
iocInit.argtypes = ()

epicsExit = libmiscIoc.epicsExit
epicsExit.argtypes = ()


__all__ = [
    'get_field_offsets',
    'registryDeviceSupportAdd',
    'IOSCANPVT', 'scanIoRequest', 'scanIoInit',
    'dbLoadDatabase',
    'recGblResetAlarms',
]
