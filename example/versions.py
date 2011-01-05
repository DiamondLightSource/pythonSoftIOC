'''Version definitions for softIOC.  This is normally the first module
imported, and should only be used to establish module versions.'''

from pkg_resources import require

require('cothread==1.17')
require('iocbuilder==3.6')
