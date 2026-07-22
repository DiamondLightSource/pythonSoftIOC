import pytest

from conftest import create_random_prefix

from softioc import builder
from epicsdbbuilder import WriteRecords


def write_and_read(tmp_path):
    """Write the current set of records and return the generated .db text,
    excluding the timestamped disclaimer header."""
    path = str(tmp_path / "records.db")
    WriteRecords(path)
    return open(path).readlines()[5:]


def record_block(lines, header):
    """Returns the lines of the record() block starting with header (e.g.
    'record(ai, "PREFIX:NAME")'), for checking what's nested inside it."""
    text = ''.join(lines)
    start = text.index(header)
    end = text.index('}', start)
    return text[start:end]


# ----------------------------------------------------------------------------
# The three ways to declare an alias: all positive paths.

def test_alias_relative(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    builder.Alias('AI', 'AI_ALIAS')

    lines = write_and_read(tmp_path)
    assert '    alias("%s:AI_ALIAS")\n' % prefix in lines


def test_alias_absolute(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    builder.Alias(prefix + ':AI', 'SOME:OTHER:NAME')

    lines = write_and_read(tmp_path)
    assert '    alias("SOME:OTHER:NAME")\n' in lines


def test_alias_kwarg(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aOut('AO', alias='AO_ALIAS')

    lines = write_and_read(tmp_path)
    assert '    alias("%s:AO_ALIAS")\n' % prefix in lines


def test_add_device_alias(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('test')
    builder.aIn('AI')

    lines = write_and_read(tmp_path)
    assert '    alias("test:AI")\n' in lines


# ----------------------------------------------------------------------------
# AddDeviceAlias is forward-only, exactly like SetDeviceName: it only
# affects records (and their aliases) created after it is called.

def test_add_device_alias_only_affects_subsequent_records(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)

    builder.aIn('EARLY')
    builder.AddDeviceAlias('after')
    builder.longIn('LATE')

    lines = write_and_read(tmp_path)
    assert not any('after:EARLY' in line for line in lines)
    assert '    alias("after:LATE")\n' in lines


def test_add_device_alias_requires_device_name():
    with pytest.raises(AssertionError):
        builder.AddDeviceAlias('prefix')


def test_add_device_alias_cleared_on_device_change(tmp_path):
    prefix1 = create_random_prefix()
    builder.SetDeviceName(prefix1)
    builder.AddDeviceAlias('carried')

    prefix2 = create_random_prefix()
    builder.SetDeviceName(prefix2)
    builder.aIn('AI')

    lines = write_and_read(tmp_path)
    assert not any('carried:' in line for line in lines)


def test_add_device_alias_duplicate_prefix_raises():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('A')
    with pytest.raises(AssertionError):
        builder.AddDeviceAlias('A')


# ----------------------------------------------------------------------------
# A record's own aliases (from `alias=` or Alias()) are themselves given
# device-prefixed aliases, pointing directly at the target record -- never
# chained as an alias of another alias.

def test_add_device_alias_propagates_to_own_alias(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('A')
    builder.aOut('t', alias='a')

    lines = write_and_read(tmp_path)
    block = record_block(lines, 'record(ao, "%s:t")' % prefix)
    # All three aliases are in-body clauses on the real record "t" itself.
    assert '    alias("%s:a")\n' % prefix in block
    assert '    alias("A:t")\n' in block
    assert '    alias("A:a")\n' in block


def test_alias_call_after_add_device_alias_also_propagates(tmp_path):
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('A')
    builder.aIn('t')
    builder.Alias('t', 'a2')

    lines = write_and_read(tmp_path)
    block = record_block(lines, 'record(ai, "%s:t")' % prefix)
    assert '    alias("%s:a2")\n' % prefix in block
    assert '    alias("A:t")\n' in block
    assert '    alias("A:a2")\n' in block


# ----------------------------------------------------------------------------
# ClearRecords() frees up previously used alias names for reuse.

def test_clear_records_frees_alias_names():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    builder.Alias('AI', 'REUSED')

    builder.ClearRecords()

    # Should not raise: the record and alias from before are gone.
    builder.aIn('AI')
    builder.Alias('AI', 'REUSED')


def test_clear_records_keeps_device_alias_prefixes(tmp_path):
    # Unlike alias names, device alias prefix registrations are scoped to
    # the device, not to the set of created records, so they must survive
    # ClearRecords() -- matching how they already survive across records
    # created under the same SetDeviceName call.
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('kept')
    builder.aIn('AI')

    builder.ClearRecords()
    builder.aIn('AI')

    lines = write_and_read(tmp_path)
    assert '    alias("kept:AI")\n' in lines


# ----------------------------------------------------------------------------
# Error cases: all PV-name mistakes must raise immediately, not be deferred
# to builder.LoadDatabase()/dbLoadDatabase() time.

def test_alias_target_not_found():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    with pytest.raises(AssertionError):
        builder.Alias('DOES_NOT_EXIST', 'ALIAS')


def test_alias_name_taken_by_existing_alias():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    builder.aOut('AO')
    builder.Alias('AI', 'DUP')
    with pytest.raises(AssertionError):
        builder.Alias('AO', 'DUP')


def test_alias_name_taken_by_existing_record():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    builder.aOut('AO')
    with pytest.raises(AssertionError):
        builder.Alias('AI', 'AO')


def test_alias_kwarg_name_collision():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI', alias='DUP')
    with pytest.raises(AssertionError):
        builder.aOut('AO', alias='DUP')


def test_record_name_taken_by_existing_alias():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    builder.Alias('AI', 'TAKEN')
    with pytest.raises(AssertionError):
        builder.aOut('TAKEN')


def test_device_alias_collision_with_existing_record():
    # Device U already owns a real record whose name exactly matches what
    # device T's AddDeviceAlias(U) would generate for a same-named PV.
    prefix_u = create_random_prefix()
    builder.SetDeviceName(prefix_u)
    builder.aIn('thing')

    prefix_t = create_random_prefix()
    builder.SetDeviceName(prefix_t)
    builder.AddDeviceAlias(prefix_u)
    with pytest.raises(AssertionError):
        builder.aIn('thing')


def test_absolute_alias_name_too_long():
    # Absolute (colon-containing) names bypass epicsdbbuilder's own
    # relative-name length check, so alias.resolve_name must apply it
    # directly instead of silently accepting an over-long name.
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.aIn('AI')
    too_long = 'A:' + 'X' * 70
    with pytest.raises(AssertionError):
        builder.Alias('AI', too_long)


def test_device_alias_prefix_too_long_is_caught_eagerly():
    # A pathological AddDeviceAlias prefix generates a device-prefixed
    # alias name via raw string substitution rather than resolve_name's
    # normal relative-name path -- but since the generated name contains a
    # colon, add_alias's call to resolve_name still catches it via the
    # absolute-name length check, rather than a long enough generated name
    # crashing the EPICS database parser's scanner at LoadDatabase() time.
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('X' * 20000)
    with pytest.raises(AssertionError):
        builder.aIn('AI')


def test_add_device_alias_requires_string_prefix():
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    with pytest.raises(AssertionError):
        builder.AddDeviceAlias('')
    with pytest.raises(AssertionError):
        builder.AddDeviceAlias(None)


def test_absolute_alias_skips_device_alias_propagation(tmp_path):
    # An absolute alias has no device-relative part to substitute a device
    # alias prefix into, so unlike a relative alias it's added as a single
    # alias with no propagation, and no "A:..." counterpart is generated
    # for it -- but this must not raise, unlike an absolute alias failing
    # to substitute for a record's own (always device-relative) name.
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('A')
    builder.aIn('t')
    builder.Alias('t', 'SOME:ABSOLUTE:NAME')

    lines = write_and_read(tmp_path)
    block = record_block(lines, 'record(ai, "%s:t")' % prefix)
    assert '    alias("A:t")\n' in block
    assert '    alias("SOME:ABSOLUTE:NAME")\n' in block
    assert block.count('alias(') == 2


def test_add_device_alias_cannot_apply_under_nested_prefix():
    # epicsdbbuilder's PushPrefix/PopPrefix (reachable via builder even
    # though not part of softioc's documented API) can put a record under a
    # name that doesn't start with the device prefix _device_prefix() reads
    # off the top of the stack -- this must raise rather than silently
    # produce no device alias for that record.
    from epicsdbbuilder import PushPrefix, PopPrefix
    prefix = create_random_prefix()
    builder.SetDeviceName(prefix)
    builder.AddDeviceAlias('A')
    PushPrefix('SUB')
    try:
        with pytest.raises(AssertionError):
            builder.aIn('rec')
    finally:
        PopPrefix()
