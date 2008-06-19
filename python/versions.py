'''Version definitions for softIOC.  This is normally the first module
imported, and should only be used to establish module versions.'''

import sys
from pkg_resources import require

require('cothread==1.6')
require('dls.builder==1.3')
