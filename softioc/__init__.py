'''Python soft IOC module.'''
import os

from epicscorelibs import path
from epicscorelibs.ioc import \
    iocshRegisterCommon, registerRecordDeviceDriver, pdbbase

# Do this as early as possible, in case we happen to use cothread
# This will set the CATOOLS_LIBCA_PATH environment variable in case we use
# cothread.catools. It works even if we don't have cothread installed
import epicscorelibs.path.cothread  # noqa

# This import will also pull in the extension, which is needed
# before we call iocshRegisterCommon
from .imports import dbLoadDatabase
from ._version_git import __version__

# Need to do this before calling anything in device.py
iocshRegisterCommon()
for dbd in ('base.dbd', 'PVAServerRegister.dbd', 'qsrv.dbd'):
    dbLoadDatabase(dbd, os.path.join(path.base_path, 'dbd'), None)
iocStats = os.path.join(os.path.dirname(__file__), "iocStats", "devIocStats")
dbLoadDatabase('devIocStats.dbd', iocStats, None)

if registerRecordDeviceDriver(pdbbase):
    raise RuntimeError('Error registering')

__all__ = ['__version__']
