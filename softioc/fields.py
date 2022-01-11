'''Access to fields within a record structure.'''

from __future__ import print_function

import sys
from ctypes import *
from .imports import get_field_offsets, get_DBF_values
import numpy

from epicscorelibs.ca.dbr import *
from epicscorelibs.ca.dbr import ca_timestamp, EPICS_epoch


# Pick up the DBF_ definitions from the C helper layer.  This is safer than
# defining the values here, as unfortunately the values have been known to
# change between EPICS releases.
for name, value in get_DBF_values().items():
    globals()[name] = value


# Mapping from record field type to ctypes type.  Type STRING is handled
# specially, and types ENUM, MENU, DEVICE and FWDLINK aren't supported.
#
# (The translation for DBF_ULONG is c_int32 rather than c_uint32 because this
# gets turned into the long Python type, which ends up causing grief
# downstream for no good purpose -- for example, enums are of type DBF_ULONG,
# but this cannot be written with caput.)
DbfCodeToCtypes = {
    DBF_STRING: c_char * 40,
    DBF_CHAR: c_byte,
    DBF_UCHAR: c_ubyte,
    DBF_SHORT: c_int16,
    DBF_USHORT: c_uint16,
    DBF_LONG: c_int32,
    DBF_ULONG: c_int32,    # Should be uint32, but causes trouble later.
    DBF_FLOAT: c_float,
    DBF_DOUBLE: c_double,
    DBF_ENUM: c_uint16,
    DBF_MENU: c_uint16,
    DBF_INLINK: c_char_p,
    DBF_OUTLINK: c_char_p,
    DBF_NOACCESS: c_void_p,
}

# Mapping from basic DBR_ codes to DBF_ values
DbrToDbfCode = {
    DBR_STRING: DBF_STRING,
    DBR_SHORT: DBF_SHORT,
    DBR_FLOAT: DBF_FLOAT,
    DBR_ENUM: DBF_ENUM,
    DBR_CHAR: DBF_CHAR,
    DBR_LONG: DBF_LONG,
    DBR_DOUBLE: DBF_DOUBLE
}


class RecordFactory(object):
    def __init__(self, record_type, fields):
        '''Uses the EPICS static database to discover the offset in the record
        type and the size of each of the specified fields.'''
        self.fields = get_field_offsets(record_type)
        missing = set(fields) - set(self.fields)
        assert not missing, \
            'Fields not supported by %s: %s' % (record_type, sorted(missing))

    def __call__(self, record):
        '''Converts a raw pointer to a record structure into a _Record object
        with automatic access to fields configured in the original call to
        the constructor.'''
        return _Record(self.fields, record)


class _Record(object):
    '''Wraps record together with field definitions.'''

    def __init__(self, fields, record):
        self.__dict__['fields'] = fields
        self.__dict__['record'] = c_void_p(record)
        # This trick allows us to pass the record back to a ctype function.
        self.__dict__['_as_parameter_'] = record

    def __getattr__(self, field):
        offset, size, field_type = self.fields[field]
        address = c_void_p(offset + self.record.value)

        if field == 'TIME':
            return self.__get_time(address)
        elif field_type == DBF_STRING:
            raw_string = string_at(cast(address, c_char_p))
            return raw_string.decode(errors = 'replace')
        elif field_type in [DBF_INLINK, DBF_OUTLINK]:
            raw_string = cast(address, POINTER(c_char_p))[0]
            return raw_string.decode(errors = 'replace')
        else:
            ctypes_type = DbfCodeToCtypes[field_type]
            return cast(address, POINTER(ctypes_type))[0]

    def __setattr__(self, field, value):
        offset, size, field_type = self.fields[field]
        address = c_void_p(offset + self.record.value)

        if field == 'TIME':
            self.__set_time(address, value)
        elif field_type == DBF_STRING:
            value = str(value).encode()
            buffer = create_string_buffer(value)
            if size > len(value) + 1:
                size = len(value) + 1
            memmove(address, buffer, size)
        else:
            ctypes_type = DbfCodeToCtypes[field_type]
            cast(address, POINTER(ctypes_type))[0] = value

    # Directly write EPICS compatible value to .VAL field
    def write_val(self, value):
        offset, size, field_type = self.fields['VAL']
        address = c_void_p(offset + self.record.value)

        ctypes_type = DbfCodeToCtypes[field_type]
        assert sizeof(value) == size, \
            'Incompatible field and value: %d %d' % (sizeof(value), size)
        cast(address, POINTER(ctypes_type))[0] = value

    def read_val(self):
        offset, size, field_type = self.fields['VAL']
        address = c_void_p(offset + self.record.value)
        ctypes_type = DbfCodeToCtypes[field_type]
        return cast(address, POINTER(ctypes_type)).contents


    def __get_time(self, address):
        timestamp = cast(address, POINTER(ca_timestamp))[0]
        timestamp.secs += EPICS_epoch
        return timestamp

    def __set_time(self, address, new_time):
        address = cast(address, POINTER(ca_timestamp))
        if isinstance(new_time, ca_timestamp):
            address[0] = new_time
        else:
            # Assume the timestamp is a floating point
            address[0].secs = int(new_time)
            address[0].nsec = int(1e9 * (new_time % 1.0))
        # Fixup the EPICS epoch offset: this never shows outside low level
        # library access.
        address[0].secs -= EPICS_epoch



__all__ = ['RecordFactory', 'DbfCodeToNumpy', 'ca_timestamp']
