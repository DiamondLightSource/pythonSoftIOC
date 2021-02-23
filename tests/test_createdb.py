# Python script to create a .db file

import sys

import versions
import testing

from softioc.builder import WriteRecords
WriteRecords(sys.argv[1])
