'''Python soft IOC module.'''
import os

from epicscorelibs import path
from epicscorelibs.ioc import \
    iocshRegisterCommon, registerRecordDeviceDriver, pdbbase

# This import will also pull in the extension, which is needed
# before we call iocshRegisterCommon
from .imports import dbLoadDatabase
from ._version_git import __version__

# Need to do this before calling anything in device.py
iocshRegisterCommon()
for dbd in ('base.dbd', 'PVAServerRegister.dbd', 'qsrv.dbd'):
    dbLoadDatabase(dbd, os.path.join(path.base_path, "dbd"), None)
dbLoadDatabase("devIocStats.dbd", os.path.dirname(__file__), None)

if registerRecordDeviceDriver(pdbbase):
    raise RuntimeError('Error registering')

__all__ = ["__version__"]
