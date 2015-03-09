'''Version definitions for softIOC.  This is normally the first module
imported, and should only be used to establish module versions.'''

from pkg_resources import require

require('cothread==2.9')
require('epicsdbbuilder==1.0')
