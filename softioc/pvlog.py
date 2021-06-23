# Support for PV put logging
#
# Importing this module configures PV put logging

import os
from . import imports

imports.install_pv_logging(
    os.path.join(os.path.dirname(__file__), 'access.acf'))
