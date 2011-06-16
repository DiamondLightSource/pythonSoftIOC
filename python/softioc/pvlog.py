# Support for PV put logging
#
# Importing this module configures PV put logging

import os
from imports import EpicsDll, libPythonSupport

libasIoc = EpicsDll('asIoc')

EpicsPvPutHook = libPythonSupport.EpicsPvPutHook
asSetFilename = libasIoc.asSetFilename
asTrapWriteRegisterListener = libasIoc.asTrapWriteRegisterListener

asSetFilename(os.path.join(os.path.dirname(__file__), '..', 'access.acf'))
asTrapWriteRegisterListener(EpicsPvPutHook)
