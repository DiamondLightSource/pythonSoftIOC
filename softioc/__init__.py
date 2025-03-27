'''Python soft IOC module.'''
import os

import epicscorelibs.path
from epicscorelibs.ioc import iocshRegisterCommon, pdbbase

# Do this as early as possible, in case we happen to use cothread
# This will set the CATOOLS_LIBCA_PATH environment variable in case we use
# cothread.catools. It works even if we don't have cothread installed
import epicscorelibs.path.cothread  # noqa

# This import will also pull in the extension, which is needed
# before we call iocshRegisterCommon
from .imports import dbLoadDatabase, registerRecordDeviceDriver
from ._version_git import __version__

# Need to do this before calling anything in device.py
iocshRegisterCommon()
base_dbd_path = os.path.join(epicscorelibs.path.base_path, 'dbd')
dbLoadDatabase('base.dbd', base_dbd_path, None)
iocStats = os.path.join(os.path.dirname(__file__), "iocStats", "devIocStats")
dbLoadDatabase('devIocStats.dbd', iocStats, None)

registerRecordDeviceDriver(pdbbase)

__all__ = ['__version__']
