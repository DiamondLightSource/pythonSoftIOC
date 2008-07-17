'''Version definitions for softIOC.  This is normally the first module
imported, and should only be used to establish module versions.'''

import sys
from pkg_resources import require

require('numpy==1.1.0')
require('cothread==1.8')
require('dls.builder==1.3')
