'''External DLL imports used for implementing Python EPICS device support.
'''

import os.path
from ctypes import *


libPythonSupport = CDLL('libPythonSupport.so')

# void get_field_offsets(
#     const char * record_type, const char * field_names[], int field_count,
#     short field_offset[], short field_size[], short field_type[])
#
# Looks up field offset, size and type values for the given record type and
# the given list of field names.
get_field_offsets = libPythonSupport.get_field_offsets
get_field_offsets.restype = None
# get_field_offsets.argtypes = (
#     c_char_p, c_void_p, c_int, c_void_p, c_void_p, c_void_p)


# char * get_EPICS_BASE()
#
# Returns the path to EPICS_BASE
get_EPICS_BASE = libPythonSupport.get_EPICS_BASE
get_EPICS_BASE.restype = c_char_p
get_EPICS_BASE.argtypes = ()


EPICS_BASE = get_EPICS_BASE()

def EpicsDll(dll):
    return CDLL(os.path.join(EPICS_BASE, 'lib/linux-x86', 'lib%s.so' % dll))

    
libregistryIoc = EpicsDll('registryIoc')
libdbIoc = EpicsDll('dbIoc')
libmiscIoc = EpicsDll('miscIoc')


def expect_success(status, function, args):
    assert status == 0, 'Expected success'

def expect_true(status, function, args):
    assert status, 'Expected True'

    
# int registryDeviceSupportAdd(
#     const char *name,const struct dset *pdset);
#
# Registers device support.
registryDeviceSupportAdd = libregistryIoc.registryDeviceSupportAdd
registryDeviceSupportAdd.restype = c_int
# registryDeviceSupportAdd.argtypes = (c_char_p, c_void_p)
registryDeviceSupportAdd.errcheck = expect_true


# void scanIoInit(IOSCANPVT *)
# void scanIoRequest(IOSCANPVT *)
#
# Initialise and trigger I/O Intr processing structure.
IOSCANPVT = c_void_p

scanIoInit = libdbIoc.scanIoInit
scanIoInit.restype = None
# scanIoInit.argtypes = (IOSCANPVT,)

scanIoRequest = libdbIoc.scanIoRequest
scanIoRequest.restype = None
# scanIoRequest.argtypes = (IOSCANPVT,)

dbLoadDatabase = libdbIoc.dbLoadDatabase
dbLoadDatabase.argtypes = (c_char_p, c_char_p, c_char_p)
dbLoadDatabase.errcheck = expect_success

dbl = libdbIoc.dbl
dbl.argtypes = (c_char_p, c_char_p)


# unsigned short recGblResetAlarms(void *precord)
#
# Raises event processing if any alarm status has changed, and resets NSTA
# and NSEV fields for further processing.
recGblResetAlarms = libdbIoc.recGblResetAlarms
recGblResetAlarms.restype = c_short
# recGblResetAlarms.argtypes = (c_void_p,)


iocInit = libmiscIoc.iocInit
iocInit.argtypes = ()


__all__ = [
    'get_field_offsets',
    'registryDeviceSupportAdd',
    'IOSCANPVT', 'scanIoRequest', 'scanIoInit',
    'dbLoadDatabase',
    'recGblResetAlarms',
]
