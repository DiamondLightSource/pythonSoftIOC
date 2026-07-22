'''Support for adding aliases to EPICS records.

An alias is an alternative name by which an existing record can be reached.
This module resolves alias and target names relative to the current device
name (see `softioc.builder.SetDeviceName`), validates names eagerly so that
mistakes are reported when they are made rather than when the generated
database is loaded, and glues together the alias support already provided
by `epicsdbbuilder`.
'''

from epicsdbbuilder import GetRecordNames, LookupRecord


def _validate_length(full_name):
    # GetRecordNames() already length-checks relative record names as they
    # are resolved, but that's not the only way a name reaches us: absolute
    # names bypass it, and so does device-alias-prefix substitution (which
    # builds a name by string surgery, not by resolving it).  Applied
    # uniformly here so every alias name is checked no matter how it was
    # constructed, catching e.g. a pathological AddDeviceAlias prefix that
    # would otherwise generate a name long enough to crash the EPICS
    # database parser instead of failing cleanly in Python.
    max_length = GetRecordNames().maxLength
    shown = full_name if len(full_name) <= 80 else full_name[:80] + '...'
    assert 0 < len(full_name) <= max_length, \
        'Record name %r too long' % shown


def resolve_name(name):
    '''Resolves name to an absolute record name.  If name contains a colon
    it is treated as already absolute, otherwise it is resolved relative to
    the current device name.'''
    if ':' in name:
        full_name = name
    else:
        full_name = GetRecordNames()(name)
    _validate_length(full_name)
    return full_name


# Every alias name declared so far this session, mapping the full alias
# name to the record it aliases.  Real record names are already tracked by
# epicsdbbuilder (LookupRecord); this supplements that with alias names, so
# collisions between the two are caught immediately rather than only when
# the generated database is loaded.
_alias_names = {}


def _lookup_record(full_name):
    '''Returns the record called full_name, or None if no such record has
    been created.'''
    try:
        return LookupRecord(full_name)
    except KeyError:
        return None


def check_record_name(name):
    '''Called before creating a new record: raises if name is already in
    use as an alias.  (A collision with an existing record is already
    caught by epicsdbbuilder itself.)'''
    full_name = resolve_name(name)
    assert full_name not in _alias_names, \
        'Alias %r already defined' % full_name


def add_alias(record, alias_name):
    '''Adds alias_name as an alias for record.  If alias_name is relative
    (no colon), it is resolved under the current device name and also
    propagated to every registered device alias prefix, exactly like the
    record's own name.  If alias_name is absolute (contains a colon), it
    is added as a single alias with no propagation: an absolute name has
    no device-relative part to substitute a device alias prefix into.'''
    full_alias = resolve_name(alias_name)
    assert full_alias not in _alias_names, \
        'Alias %r already defined' % full_alias
    assert _lookup_record(full_alias) is None, \
        'Record %r already defined' % full_alias
    record.add_alias(full_alias)
    _alias_names[full_alias] = record
    if ':' not in alias_name:
        _propagate_device_alias(record, full_alias)


def create_alias(name, alias_name):
    '''Creates alias_name as an alias for the record called name.  Both
    name and alias_name may be relative to the current device name or
    absolute.  The target record must already have been created earlier in
    this session.'''
    full_name = resolve_name(name)
    record = _lookup_record(full_name)
    assert record is not None, \
        'Cannot alias unknown record %r' % full_name
    add_alias(record, alias_name)


# -----------------------------------------------------------------------
# Support for AddDeviceAlias.  Like SetDeviceName, this only affects
# records (and their own aliases) created after it is called.

# Alias prefixes registered for the current device.
_device_aliases = []


def _device_prefix():
    '''Returns (prefix, separator) for the current device, or (None, None)
    if no device name is currently set.'''
    names = GetRecordNames()
    if names.prefix:
        return names.prefix[-1], names.separator
    else:
        return None, None


def _propagate_device_alias(record, full_name):
    '''Called for a record's own primary name (from register_record) or a
    relative alias (from add_alias): if any device alias prefixes are
    registered, adds a copy of full_name under each prefix, pointing
    directly at record.

    The names generated here (e.g. "A:t") always contain a colon, so
    add_alias treats them as absolute and never propagates them again --
    there is no alias-of-alias chaining.

    If device alias prefixes are registered but full_name isn't actually
    part of the current device (e.g. a nested epicsdbbuilder PushPrefix is
    in play), there is no sensible substitution to make.  Silently
    skipping it would mean AddDeviceAlias quietly failing to do its job
    for that name, so this raises instead.'''
    if not _device_aliases:
        return
    device_prefix, separator = _device_prefix()
    assert device_prefix is not None, \
        'No device name set while device alias prefixes are registered'
    assert full_name.startswith(device_prefix + separator), \
        'Cannot apply device alias prefixes to %r: not part of the ' \
        'current device %r' % (full_name, device_prefix)
    short_name = full_name[len(device_prefix) + len(separator):]
    for prefix in _device_aliases:
        add_alias(record, separator.join((prefix, short_name)))


def register_record(record):
    '''Called for every record created.  Applies any device alias prefixes
    already registered with AddDeviceAlias to the record's primary name.'''
    _propagate_device_alias(record, record.name)


def add_device_alias(prefix):
    '''Registers prefix as an alias prefix for the current device.  Only
    affects records (and their aliases) created after this call, exactly
    as SetDeviceName only affects subsequently created records.'''
    assert isinstance(prefix, str) and prefix, \
        'AddDeviceAlias prefix must be a non-empty string'
    assert prefix not in _device_aliases, \
        'Device alias prefix %r already registered' % prefix
    _device_aliases.append(prefix)


def clear_device_aliases():
    '''Called whenever the device name changes (SetDeviceName/UnsetDevice):
    forgets alias prefix registrations, as they are only meaningful for the
    device they were registered against.'''
    _device_aliases.clear()


def forget_all():
    '''Called when all created records are discarded (ClearRecords):
    forgets every alias name declared so far, since the records behind
    them are gone.  Alias prefix registrations for the (unchanged) device
    survive, matching SetDeviceName's scoping.'''
    _alias_names.clear()
