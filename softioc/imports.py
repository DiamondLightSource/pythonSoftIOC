'''External DLL imports used for implementing Python EPICS device support.
'''

import sys
from ctypes import *

# Use the libs with the right windows flags
from epicscorelibs.ioc import dbCore, Com

from . import _extension


# These are in the extension
def get_DBF_values():
    """Return {DBF_name: DBF_int_value} mapping"""
    return _extension.get_DBF_values()

def get_field_offsets(record_type):
    """Return {field_name: (offset, size, field_type)}"""
    return _extension.get_field_offsets(record_type)

def db_put_field(name, dbr_type, pbuffer, length):
    """Put field where pbuffer is void* pointer. Returns RC"""
    return _extension.db_put_field(name, dbr_type, pbuffer, length)

def install_pv_logging(acf_file):
    """Install pv logging"""
    _extension.install_pv_logging(acf_file)

def expect_success(status, function, args):
    assert status == 0, 'Expected success'

def expect_true(status, function, args):
    assert status, 'Expected True'


if sys.version_info < (3,):
    # Python 2
    auto_encode = c_char_p
    def auto_decode(result, func, args):
        return result

else:
    # Python 3

    # Encode all strings to c_char_p
    class auto_encode(c_char_p):
        encoded = []
        @classmethod
        def from_param(cls, value):
            if value is None:
                return value
            else:
                return value.encode()

    def auto_decode(result, func, args):
        return result.decode()


# int registryDeviceSupportAdd(
#     const char *name,const struct dset *pdset);
#
# Registers device support.
registryDeviceSupportAdd = dbCore.registryDeviceSupportAdd
registryDeviceSupportAdd.argtypes = (c_char_p, c_void_p)
registryDeviceSupportAdd.errcheck = expect_true


# void scanIoInit(IOSCANPVT *)
# void scanIoRequest(IOSCANPVT *)
#
# Initialise and trigger I/O Intr processing structure.
IOSCANPVT = c_void_p

scanIoInit = dbCore.scanIoInit
scanIoInit.argtypes = (IOSCANPVT,)
scanIoInit.restype = None

scanIoRequest = dbCore.scanIoRequest
scanIoRequest.argtypes = (IOSCANPVT,)
scanIoRequest.restype = None

dbLoadDatabase = dbCore.dbLoadDatabase
dbLoadDatabase.argtypes = (auto_encode, auto_encode, auto_encode)
dbLoadDatabase.errcheck = expect_success


# unsigned short recGblResetAlarms(void *precord)
#
# Raises event processing if any alarm status has changed, and resets NSTA
# and NSEV fields for further processing.
recGblResetAlarms = dbCore.recGblResetAlarms
recGblResetAlarms.argtypes = (c_void_p,)
recGblResetAlarms.restype = c_short

iocInit = dbCore.iocInit
iocInit.argtypes = ()

epicsExit = Com.epicsExit
epicsExit.argtypes = ()


__all__ = [
    'get_field_offsets',
    'registryDeviceSupportAdd',
    'IOSCANPVT', 'scanIoRequest', 'scanIoInit',
    'dbLoadDatabase',
    'recGblResetAlarms',
]
