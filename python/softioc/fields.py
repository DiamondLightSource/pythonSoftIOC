'''Access to fields within a record structure.'''

from __future__ import print_function

import sys
from ctypes import *
from .imports import get_field_offsets
import numpy

from cothread.dbr import *
from cothread.dbr import ca_timestamp, EPICS_epoch


# Record field types, as defined in dbFldTypes.h
DBF_STRING      = 0
DBF_CHAR        = 1
DBF_UCHAR       = 2
DBF_SHORT       = 3
DBF_USHORT      = 4
DBF_LONG        = 5
DBF_ULONG       = 6
DBF_FLOAT       = 7
DBF_DOUBLE      = 8
DBF_ENUM        = 9
DBF_MENU        = 10
DBF_DEVICE      = 11
DBF_INLINK      = 12
DBF_OUTLINK     = 13
DBF_FWDLINK     = 14
DBF_NOACCESS    = 15

# Mapping from record field type to ctypes type.  Type STRING is handled
# specially, and types ENUM, MENU, DEVICE and FWDLINK aren't supported.
#
# (The translation for DBF_ULONG is c_int32 rather than c_uint32 because this
# gets turned into the long Python type, which ends up causing grief
# downstream for no good purpose -- for example, enums are of type DBF_ULONG,
# but this cannot be written with caput.)
DbfCodeToCtypes = {
    DBF_CHAR :      c_byte,
    DBF_UCHAR :     c_ubyte,
    DBF_SHORT :     c_int16,
    DBF_USHORT :    c_uint16,
    DBF_LONG :      c_int32,
    DBF_ULONG :     c_int32,    # Should be uint32, but causes trouble later.
    DBF_FLOAT :     c_float,
    DBF_DOUBLE :    c_double,
    DBF_ENUM :      c_uint16,
    DBF_MENU :      c_uint16,
    DBF_INLINK :    c_char_p,
    DBF_OUTLINK :   c_char_p,
    DBF_NOACCESS :  c_void_p,
}

# Mapping for record field type to numpy type.
DbfCodeToNumpy = {
    DBF_STRING :    numpy.dtype('S40'),
    DBF_CHAR :      numpy.dtype('int8'),
    DBF_UCHAR :     numpy.dtype('uint8'),
    DBF_SHORT :     numpy.dtype('int16'),
    DBF_USHORT :    numpy.dtype('uint16'),
    DBF_LONG :      numpy.dtype('int32'),
    DBF_ULONG :     numpy.dtype('uint32'),
    DBF_FLOAT :     numpy.dtype('float32'),
    DBF_DOUBLE :    numpy.dtype('float64'),
}

# Mapping from basic DBR_ codes to DBF_ values
DbrToDbfCode = {
    DBR_STRING :    DBF_STRING,
    DBR_SHORT :     DBF_SHORT,
    DBR_FLOAT :     DBF_FLOAT,
    DBR_ENUM :      DBF_ENUM,
    DBR_CHAR :      DBF_CHAR,
    DBR_LONG :      DBF_LONG,
    DBR_DOUBLE :    DBF_DOUBLE
}


if sys.version_info >= (3,):
    def decode(string):
        return string.decode()
    def encode(string):
        return string.encode()
else:
    def decode(string):
        return string
    def encode(string):
        return string


class RecordFactory(object):
    def __init__(self, record_type, fields):
        '''Uses the EPICS static database to discover the offset in the record
        type and the size of each of the specified fields.'''
        length = len(fields)
        field_name_strings = [
            create_string_buffer(field.encode())
            for field in fields]

        field_names = (c_void_p * len(field_name_strings))()
        for i, field in enumerate(field_name_strings):
            field_names[i] = addressof(field)

        field_offsets = numpy.empty(length, dtype = numpy.int16)
        field_sizes   = numpy.zeros(length, dtype = numpy.int16)
        field_types   = numpy.empty(length, dtype = numpy.int16)

        get_field_offsets(
            record_type, field_names, length,
            field_offsets.ctypes.data_as(c_void_p),
            field_sizes.ctypes.data_as(c_void_p),
            field_types.ctypes.data_as(c_void_p))
        assert field_sizes.all(), 'At least one field seems to be missing'

        # The following rather convoluted expression converts the separate
        # arrays of field names and attributes into a dictionary looking up
        # each field and returning the appropriate list of attributes.
        #     One final adjustment needed is that all the numpy.int16 values
        # need to be converted back into regular integers to ensure good
        # processing downstream.
        self.fields = dict(zip(fields, zip(
            *map(lambda l: map(int, l),
                (field_offsets, field_sizes, field_types)))))

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
            return decode(string_at(string_at(cast(address, c_char_p), 40)))
        elif field_type in [DBF_INLINK, DBF_OUTLINK]:
            return decode(cast(address, POINTER(c_char_p))[0])
        else:
            ctypes_type = DbfCodeToCtypes[field_type]
            return cast(address, POINTER(ctypes_type))[0]

    def __setattr__(self, field, value):
        offset, size, field_type = self.fields[field]
        address = c_void_p(offset + self.record.value)

        if field == 'TIME':
            self.__set_time(address, value)
        elif field_type == DBF_STRING:
            value = encode(str(value))
            buffer = create_string_buffer(value)
            if size > len(value) + 1:
                size = len(value) + 1
            memmove(address, buffer, size)
        else:
            ctypes_type = DbfCodeToCtypes[field_type]
            cast(address, POINTER(ctypes_type))[0] = value

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
