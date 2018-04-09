'''Version definitions for softIOC.  This is normally the first module
imported, and should only be used to establish module versions.'''

from pkg_resources import require

require('numpy==1.11.1')
require('cothread==2.14')
require('epicsdbbuilder==1.2')
