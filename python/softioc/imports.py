'''External DLL imports used for implementing Python EPICS device support.
'''

import os
import os.path
import sys
from ctypes import *


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


libPythonSupport = CDLL('libPythonSupport.so')

# void get_field_offsets(
#     const char * record_type, const char * field_names[], int field_count,
#     short field_offset[], short field_size[], short field_type[])
#
# Looks up field offset, size and type values for the given record type and
# the given list of field names.
get_field_offsets = libPythonSupport.get_field_offsets
get_field_offsets.argtypes = (
    auto_encode, c_void_p, c_int, c_void_p, c_void_p, c_void_p)
get_field_offsets.restype = None

# int db_put_field(const char *name, short dbrType, void *pbuffer, long length)
#
# Updates value in given field through channel access, so notifications are
# generated as appropriate.
db_put_field = libPythonSupport.db_put_field
db_put_field.argtypes = (auto_encode, c_int, c_void_p, c_long)
db_put_field.errcheck = expect_success


# char * get_EPICS_BASE()
#
# Returns the path to EPICS_BASE
get_EPICS_BASE = libPythonSupport.get_EPICS_BASE
get_EPICS_BASE.argtypes = ()
get_EPICS_BASE.restype = c_char_p
get_EPICS_BASE.errcheck = auto_decode


# void EpicsPvPutHook(struct asTrapWriteMessage *pmessage, int after)
#
# Hook for logging EPICS caput events
EpicsPvPutHook = libPythonSupport.EpicsPvPutHook


EPICS_BASE = get_EPICS_BASE()
EPICS_HOST_ARCH = os.environ['EPICS_HOST_ARCH']

def EpicsDll(dll):
    return CDLL(
        os.path.join(EPICS_BASE, 'lib', EPICS_HOST_ARCH, 'lib%s.so' % dll))

# A bit tricky: in more recent versions of EPICS all the entry points we want
# have been gathered into a single .so, but previously they were split among
# four different ones.  Just try both options.
try:
    libdbCore = EpicsDll('dbCore')
    libregistryIoc = libdbCore
    libdbIoc = libdbCore
    libmiscIoc = libdbCore
    libasIoc = libdbCore
except OSError:
    # Ok, no dbCore, then we should find everything in these four instead.
    libregistryIoc = EpicsDll('registryIoc')
    libdbIoc = EpicsDll('dbIoc')
    libmiscIoc = EpicsDll('miscIoc')
    libasIoc = EpicsDll('asIoc')



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
dbLoadDatabase.argtypes = (auto_encode, auto_encode, auto_encode)
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


# Import for libas

# int asSetFilename(const char *acf)
#
# Set access control file
asSetFilename = libasIoc.asSetFilename
asSetFilename.argtypes = (auto_encode,)

# asTrapWriteId asTrapWriteRegisterListener(asTrapWriteListener func)
#
# Install caput hook
asTrapWriteRegisterListener = libasIoc.asTrapWriteRegisterListener


__all__ = [
    'get_field_offsets',
    'registryDeviceSupportAdd',
    'IOSCANPVT', 'scanIoRequest', 'scanIoInit',
    'dbLoadDatabase',
    'recGblResetAlarms',
]
