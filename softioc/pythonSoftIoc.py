'''Device support files for pythonSoftIoc Python EPICS device support.

Note that these definitions don't strictly need to be loaded through the
iocbuilder in this way, but it makes structural sense this way.'''


import epicsdbbuilder
from . import device


class RecordWrapper(object):
    '''This class wraps both a builder and a Python device record instance.
    From the outside it looks like a builder record until the database is
    written.'''

    __Instances = []
    __builder_reset = False

    def __init__(self, builder, device, name, **fields):
        assert not self.is_builder_reset(), \
            'It\'s too late to create records'
        # List of keyword arguments expected by the device constructor.  The
        # remaining arguments are passed to the builder.  It's a shame we
        # have to maintain this separately from the corresponding device list.
        DeviceKeywords = [
            'on_update', 'on_update_name', 'validate', 'always_update',
            'initial_value', '_wf_nelm', '_wf_dtype', 'blocking']
        device_kargs = {}
        for keyword in DeviceKeywords:
            if keyword in fields:
                device_kargs[keyword] = fields.pop(keyword)

        record = builder(name, **fields)
        record.address = '@' + record.name
        self.__set('__builder', record)
        self.__set('__device',  device(record.name, **device_kargs))
        self.__Instances.append(self)

    def __set(self, field, value):
        if field[:2] == '__' and field[-2:] != '__':
            field = '_' + self.__class__.__name__ + field
        self.__dict__[field] = value

    @classmethod
    def reset_builder(cls):
        cls.__builder_reset = True
        for instance in cls.__Instances:
            instance.__set('__builder', None)

    @classmethod
    def is_builder_reset(cls):
        '''Returns True if it is too late to create records'''
        return cls.__builder_reset



    # Most attributes delegate directly to the builder instance until the
    # database has been written.  At this point the builder instance has been
    # deleted, and an attribute error will be raised instead.

    def __getattr__(self, field):
        try:
            return getattr(self.__device, field)
        except AttributeError:
            if self.__builder is None:
                raise
            else:
                return getattr(self.__builder, field)

    def __setattr__(self, field, value):
        if self.__builder is None:
            raise AttributeError('builder has been written')
        else:
            return setattr(self.__builder, field, value)

    # Some further "Duck typing" for the builder: the following are required
    # for links to work properly.

    def __call__(self, *specifiers):
        return self.__builder(*specifiers)

    def __str__(self):
        return str(self.__builder)



class PythonDevice(object):
    DbdFileList = ['device']

    @classmethod
    def __init_class__(cls):
        for name in [
                'ai', 'bi', 'longin',  'mbbi', 'stringin',
                'ao', 'bo', 'longout', 'mbbo', 'stringout', 'waveform']:
            builder = getattr(epicsdbbuilder.records, name)
            record = getattr(device, name)
            setattr(cls, name, cls.makeRecord(builder, record))
        cls.waveform_out = cls.makeRecord(
            epicsdbbuilder.records.waveform, device.waveform_out,
            'PythonWfOut')
        cls.long_stringin = cls.makeRecord(
            epicsdbbuilder.records.waveform, device.long_stringin,
            'PythonLongStringIn')
        cls.long_stringout = cls.makeRecord(
            epicsdbbuilder.records.waveform, device.long_stringout,
            'PythonLongStringOut')

    class makeRecord:
        def __init__(self, builder, record, dtyp = 'Python'):
            self.builder = builder
            self.record = record
            self.dtyp = dtyp

        def __call__(self, name, **fields):
            return RecordWrapper(
                self.builder, self.record, name,
                DTYP = self.dtyp, **fields)

PythonDevice.__init_class__()
