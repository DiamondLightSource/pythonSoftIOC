'''Python soft IOC module.'''
import os

# Do this as early as possible, in case we happen to use cothread
# This will set the CATOOLS_LIBCA_PATH environment variable in case we use
# cothread.catools. It works even if we don't have cothread installed
import epicscorelibs.path.cothread  # noqa

# This import will also pull in the extension, which is needed
# before we call iocshRegisterCommon
from ._version_git import __version__
from .imports import dbLoadDatabase

def load_dbd():
    import ctypes
    from epicscorelibs import path
    from epicscorelibs.ioc import \
        iocshRegisterCommon, registerRecordDeviceDriver, pdbbase
    import pvxslibs.path
    from setuptools_dso.runtime import find_dso

    dbd_paths = ':'.join([
        os.path.join(path.base_path, 'dbd'),
        pvxslibs.path.dbd_path,
        os.path.join(os.path.dirname(__file__), "iocStats", "devIocStats"),
    ])
    dbds = [
        'base.dbd', # must be first
        'devIocStats.dbd',
        'pvxsIoc.dbd',
    ]

    # Need to do this before calling anything in device.py
    iocshRegisterCommon()
    for dbd in dbds:
        dbLoadDatabase(dbd, dbd_paths, None)

    from ._extension import install_pv_logging
    dbRecStd = ctypes.CDLL(find_dso('epicscorelibs.lib.dbRecStd'), ctypes.RTLD_GLOBAL)
    pvxsIoc = ctypes.CDLL(find_dso('pvxslibs.lib.pvxsIoc'), ctypes.RTLD_GLOBAL)

    # must explicitly enable QSRV while "Feature Preview"
    os.environ.setdefault('PVXS_QSRV_ENABLE', 'YES')

    if registerRecordDeviceDriver(pdbbase):
        raise RuntimeError('Error registering')

load_dbd()
del load_dbd

__all__ = ['__version__']
