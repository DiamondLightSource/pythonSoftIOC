# Python script to create a .db file

import sys

import versions
import testing

from builder import WriteRecords
WriteRecords(sys.argv[1])
