import asyncio
import subprocess
import sys
import numpy
import os
import pytest

from conftest import (
    aioca_cleanup,
    log,
    create_random_prefix,
    requires_cothread,
    WAVEFORM_LENGTH,
    TIMEOUT,
    select_and_recv,
    get_multiprocessing_context
)

from softioc import asyncio_dispatcher, builder, softioc
from softioc import alarm
from softioc.device import SetBlocking
from softioc.device_core import LookupRecord, LookupRecordList

# Test file for miscellaneous tests related to records

# Test parameters
DEVICE_NAME = "RECORD-TESTS"

in_records = [
    builder.aIn,
    builder.boolIn,
    builder.longIn,
    builder.mbbIn,
    builder.stringIn,
    builder.WaveformIn,
]

def test_records(tmp_path):
    # Ensure we definitely unload all records that may be hanging over from
    # previous tests, then create exactly one instance of expected records.
    from sim_records import create_records
    create_records()

    path = str(tmp_path / "records.db")
    builder.WriteRecords(path)
    expected = os.path.join(os.path.dirname(__file__), "expected_records.db")
    assert open(path).readlines()[5:] == open(expected).readlines()


def test_enum_length_restriction():
    with pytest.raises(AssertionError):
        builder.mbbIn(
            "ManyLabels",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
        )

@pytest.mark.parametrize("creation_func", in_records)
def test_DISP_defaults_on(creation_func):
    """Test that all IN record types have DISP=1 set by default"""
    kwargs = {}

    if creation_func == builder.WaveformIn:
        kwargs = {"length": 1}

    record = creation_func("RECORD", **kwargs)

    # Note: DISP attribute won't exist if field not specified
    assert record.DISP.Value() == 1


def test_DISP_can_be_overridden():
    """Test that DISP can be forced off for In records"""

    record = builder.longIn("DISP-OFF", DISP=0)
    # Note: DISP attribute won't exist if field not specified
    assert record.DISP.Value() == 0


def test_waveform_construction():
    """Test the various ways to construct a Waveform records all produce
    correct results"""

    wi = builder.WaveformIn("WI1", [1, 2, 3])
    assert wi.NELM.Value() == 3

    wi = builder.WaveformIn("WI2", initial_value=[1, 2, 3, 4])
    assert wi.NELM.Value() == 4

    wi = builder.WaveformIn("WI3", length=5)
    assert wi.NELM.Value() == 5

    wi = builder.WaveformIn("WI4", NELM=6)
    assert wi.NELM.Value() == 6

    wi = builder.WaveformIn("WI5", [1, 2, 3], length=7)
    assert wi.NELM.Value() == 7

    wi = builder.WaveformIn("WI6", initial_value=[1, 2, 3], length=8)
    assert wi.NELM.Value() == 8

    wi = builder.WaveformIn("WI7", [1, 2, 3], NELM=9)
    assert wi.NELM.Value() == 9

    wi = builder.WaveformIn("WI8", initial_value=[1, 2, 3], NELM=10)
    assert wi.NELM.Value() == 10

    # Specifying neither value nor length should produce an error
    with pytest.raises(AssertionError):
        builder.WaveformIn("WI9")

    # Specifying both value and initial_value should produce an error
    with pytest.raises(AssertionError):
        builder.WaveformIn("WI10", [1, 2, 4], initial_value=[5, 6])

    # Specifying both length and NELM should produce an error
    with pytest.raises(AssertionError):
        builder.WaveformIn("WI11", length=11, NELM=12)

def test_drvhl_hlopr_defaults():
    """Test the DRVH/L and H/LOPR default settings"""
    # DRVH/L doesn't exist on In records
    ai = builder.aIn("FOO")
    # KeyError as fields with no value are simply not present in
    # epicsdbbuilder's dictionary of fields
    with pytest.raises(KeyError):
        assert ai.LOPR.Value() is None
    with pytest.raises(KeyError):
        assert ai.HOPR.Value() is None

    ao = builder.aOut("BAR")
    with pytest.raises(KeyError):
        assert ao.LOPR.Value() is None
    with pytest.raises(KeyError):
        assert ao.HOPR.Value() is None
    with pytest.raises(KeyError):
        assert ao.DRVH.Value() is None
    with pytest.raises(KeyError):
        assert ao.DRVL.Value() is None

def test_hlopr_inherits_drvhl():
    """Test that H/LOPR values are set to the DRVH/L values"""
    lo = builder.longOut("ABC", DRVH=5, DRVL=10)

    assert lo.DRVH.Value() == 5
    assert lo.HOPR.Value() == 5
    assert lo.DRVL.Value() == 10
    assert lo.LOPR.Value() == 10

def test_hlopr_dvrhl_different_values():
    """Test you can set H/LOPR and DRVH/L to different values"""
    ao = builder.aOut("DEF", DRVL=1, LOPR=2, HOPR=3, DRVH=4)

    assert ao.DRVL.Value() == 1
    assert ao.LOPR.Value() == 2
    assert ao.HOPR.Value() == 3
    assert ao.DRVH.Value() == 4

def test_pini_always_on():
    """Test that PINI is always on for in records regardless of initial_value"""
    bi = builder.boolIn("AAA")
    assert bi.PINI.Value() == "YES"

    mbbi = builder.mbbIn("BBB", initial_value=5)
    assert mbbi.PINI.Value() == "YES"

@pytest.mark.parametrize("creation_func", in_records)
def test_setting_alarm_in_records(creation_func):
    """Test that In records can have a custom alarm value set using the "status"
    and "severity" keywords"""
    kwargs = {}
    if creation_func == builder.WaveformIn:
        kwargs["length"] = 1

    record = creation_func(
        "NEW_RECORD",
        severity=alarm.MINOR_ALARM,
        status=alarm.LOLO_ALARM,
        **kwargs
    )

    assert record.STAT.Value() == "LOLO"
    assert record.SEVR.Value() == "MINOR"

@pytest.mark.parametrize("creation_func", in_records)
def test_setting_alarm_invalid_keywords(creation_func):
    """Test that In records correctly block specifying both STAT and status,
    and SEVR and severity"""

    kwargs = {}
    if creation_func == builder.WaveformIn:
        kwargs["length"] = 1

    with pytest.raises(AssertionError) as e:
        creation_func(
            "NEW_RECORD",
            severity=alarm.MINOR_ALARM,
            SEVR="MINOR",
            status=alarm.LOLO_ALARM,
            **kwargs
        )

    assert e.value.args[0] == 'Can\'t specify both severity and SEVR'

    with pytest.raises(AssertionError) as e:
        creation_func(
            "NEW_RECORD",
            severity=alarm.MINOR_ALARM,
            status=alarm.LOLO_ALARM,
            STAT="LOLO",
            **kwargs
        )

    assert e.value.args[0] == 'Can\'t specify both status and STAT'

def test_clear_records():
    """Test that clearing the known records allows creation of a record of the
    same name afterwards"""

    device_name = create_random_prefix()
    builder.SetDeviceName(device_name)

    record_name = "NEW-RECORD"

    builder.aOut(record_name)

    # First check that we cannot create two of the same name
    with pytest.raises(AssertionError):
        builder.aOut(record_name)

    builder.ClearRecords()

    # Then confirm we can create one of this name
    builder.aOut(record_name)

    # Finally prove that the underlying record holder contains only one record
    # Records are stored as full device:record name
    full_name = device_name + ":" + record_name
    assert LookupRecord(full_name)
    assert len(LookupRecordList()) == 1
    for key, val in LookupRecordList():
        assert key == full_name

def clear_records_runner(child_conn):
    """Tests ClearRecords after loading the database"""
    builder.aOut("Some-Record")
    builder.LoadDatabase()

    try:
        builder.ClearRecords()
    except AssertionError:
        # Expected error
        child_conn.send("D")  # "Done"
    child_conn.send("F")  # "Fail"

def test_clear_records_too_late():
    """Test that calling ClearRecords after a database has been loaded raises
    an exception"""
    ctx = get_multiprocessing_context()

    parent_conn, child_conn = ctx.Pipe()

    process = ctx.Process(
        target=clear_records_runner,
        args=(child_conn,),
    )

    process.start()

    try:
        select_and_recv(parent_conn, "D")
    finally:
        process.join(timeout=TIMEOUT)
        if process.exitcode is None:
            pytest.fail("Process did not terminate")


def str_ioc_test_func(device_name, conn):
    builder.SetDeviceName(device_name)

    record_name = "MyAI"

    full_name = device_name + ":" + record_name

    ai = builder.aIn(record_name)


    log("CHILD: Created ai record: ", ai.__str__())

    assert (
        ai.__str__() == full_name
    ), f"Record name {ai.__str__()} before LoadDatabase did not match " \
       f"expected string {full_name}"

    builder.LoadDatabase()

    assert (
        ai.__str__() == full_name
    ), f"Record name {ai.__str__()} after LoadDatabase did not match " \
       f"expected string {full_name}"

    dispatcher = asyncio_dispatcher.AsyncioDispatcher()
    softioc.iocInit(dispatcher)

    assert (
        ai.__str__() == full_name
    ), f"Record name {ai.__str__()} after iocInit did not match expected " \
       f"string {full_name}"

    conn.send("R")  # "Ready"
    log("CHILD: Sent R over Connection to Parent")



def test_record_wrapper_str():
    """Test that the __str__ method on the RecordWrapper behaves as expected,
    both before and after loading the record database"""

    ctx = get_multiprocessing_context()
    parent_conn, child_conn = ctx.Pipe()

    device_name = create_random_prefix()

    ioc_process = ctx.Process(
        target=str_ioc_test_func,
        args=(device_name, child_conn),
    )

    ioc_process.start()


    # Wait for message that IOC has started
    # If we never receive R it probably means an assert failed
    select_and_recv(parent_conn, "R")

def validate_fixture_names(params):
    """Provide nice names for the out_records fixture in TestValidate class"""
    return params[0].__name__

class TestValidate:
    """Tests related to the validate callback"""

    @pytest.fixture(
        params=[
            (builder.aOut, 7.89, 0),
            (builder.boolOut, 1, 0),
            (builder.Action, 1, 0),
            (builder.longOut, 7, 0),
            (builder.stringOut, "HI", ""),
            (builder.mbbOut, 2, 0),
            (builder.WaveformOut, [10, 11, 12], []),
            (builder.longStringOut, "A LONGER HELLO", ""),
        ],
        ids=validate_fixture_names
    )
    def out_records(self, request):
        """The list of Out records and an associated value to set """
        return request.param

    def validate_always_pass(self, record, new_val):
        """Validation method that always allows changes"""
        return True

    def validate_always_fail(self, record, new_val):
        """Validation method that always rejects changes"""
        return False

    def validate_ioc_test_func(
            self,
            device_name,
            record_func,
            child_conn,
            validate_pass: bool):
        """Start the IOC with the specified validate method"""

        builder.SetDeviceName(device_name)

        kwarg = {}
        if record_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

        kwarg["validate"] = (
            self.validate_always_pass
            if validate_pass
            else self.validate_always_fail
        )

        record_func("VALIDATE-RECORD", **kwarg)

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        child_conn.send("R")

        # Keep process alive while main thread runs CAGET
        if child_conn.poll(TIMEOUT):
            val = child_conn.recv()
            assert val == "D", "Did not receive expected Done character"

    def validate_test_runner(
            self,
            creation_func,
            new_value,
            expected_value,
            validate_pass: bool):

        ctx = get_multiprocessing_context()

        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.validate_ioc_test_func,
            args=(device_name, creation_func, child_conn, validate_pass),
        )

        process.start()

        from cothread.catools import caget, caput, _channel_cache

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")


            # Suppress potential spurious warnings
            _channel_cache.purge()

            kwargs = {}
            if creation_func in [builder.longStringIn, builder.longStringOut]:
                from cothread.dbr import DBR_CHAR_STR
                kwargs.update({"datatype": DBR_CHAR_STR})

            put_ret = caput(
                device_name + ":VALIDATE-RECORD",
                new_value,
                wait=True,
                **kwargs,
            )
            assert put_ret.ok, "caput did not succeed"

            ret_val = caget(
                device_name + ":VALIDATE-RECORD",
                timeout=TIMEOUT,
                **kwargs
            )

            if creation_func in [builder.WaveformOut, builder.WaveformIn]:
                assert numpy.array_equal(ret_val, expected_value)
            else:
                assert ret_val == expected_value

        finally:
            # Suppress potential spurious warnings
            _channel_cache.purge()
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)


    @requires_cothread
    def test_validate_allows_updates(self, out_records):
        """Test that record values are updated correctly when validate
        method allows it """

        creation_func, value, _ = out_records

        self.validate_test_runner(creation_func, value, value, True)


    @requires_cothread
    def test_validate_blocks_updates(self, out_records):
        """Test that record values are not updated when validate method
        always blocks updates"""

        creation_func, value, default = out_records

        self.validate_test_runner(creation_func, value, default, False)

class TestOnUpdate:
    """Tests related to the on_update callback, with and without
    always_update set"""

    @pytest.fixture(
        params=[
            builder.aOut,
            builder.boolOut,
            # builder.Action, This is just boolOut + always_update
            builder.longOut,
            builder.stringOut,
            builder.mbbOut,
            builder.WaveformOut,
            builder.longStringOut,
        ]
    )
    def out_records(self, request):
        """The list of Out records to test """
        return request.param

    def on_update_test_func(
        self, device_name, record_func, conn, always_update
    ):

        log("CHILD: Child started")

        builder.SetDeviceName(device_name)

        li = builder.longIn("ON-UPDATE-COUNTER-RECORD", initial_value=0)

        def on_update_func(new_val):
            """Increments li record each time main out record receives caput"""
            li.set(li.get() + 1)

        kwarg = {}
        if record_func is builder.WaveformOut:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

        record_func(
            "ON-UPDATE-RECORD",
            on_update=on_update_func,
            always_update=always_update,
            **kwarg)

        def on_update_done(_):
            conn.send("C")  # "Complete"
        # Put to the action record after we've done all other Puts, so we know
        # all the callbacks have finished processing
        builder.Action("ON-UPDATE-DONE", on_update=on_update_done)

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        conn.send("R")  # "Ready"

        log("CHILD: Sent R over Connection to Parent")

        # Keep process alive while main thread runs CAGET
        if conn.poll(TIMEOUT):
            val = conn.recv()
            assert val == "D", "Did not receive expected Done character"

        log("CHILD: Received exit command, child exiting")

    def on_update_runner(self, creation_func, always_update, put_same_value):

        ctx = get_multiprocessing_context()
        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.on_update_test_func,
            args=(device_name, creation_func, child_conn, always_update),
        )

        process.start()

        log("PARENT: Child started, waiting for R command")

        from cothread.catools import caget, caput, _channel_cache

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")

            log("PARENT: received R command")


            # Suppress potential spurious warnings
            _channel_cache.purge()

            # Use this number to put to records - don't start at 0 as many
            # record types default to 0 and we usually want to put a different
            # value to force processing to occur
            count = 1

            log("PARENT: begining While loop")

            while count < 4:
                put_ret = caput(
                    device_name + ":ON-UPDATE-RECORD",
                    9 if put_same_value else count,
                    wait=True,
                )
                assert put_ret.ok, f"caput did not succeed: {put_ret.errorcode}"

                log(f"PARENT: completed caput with count {count}")

                count += 1

            log("PARENT: Put'ing to DONE record")

            caput(
                device_name + ":ON-UPDATE-DONE",
                1,
                wait=True,
            )

            log("PARENT: Waiting for C command")

            # Wait for action record to process, so we know all the callbacks
            # have finished processing (This assumes record callbacks are not
            # re-ordered, and will run in the same order as the caputs we sent)
            select_and_recv(parent_conn, "C")

            log("PARENT: Received C command")

            ret_val = caget(
                device_name + ":ON-UPDATE-COUNTER-RECORD",
                timeout=TIMEOUT,
            )
            assert ret_val.ok, \
                f"caget did not succeed: {ret_val.errorcode}, {ret_val}"

            log(f"PARENT: Received val from COUNTER: {ret_val}")


            # Expected value is either 3 (incremented once per caput)
            # or 1 (incremented on first caput and not subsequent ones)
            expected_val = 3
            if put_same_value and not always_update:
                expected_val = 1

            assert ret_val == expected_val

        finally:
            # Suppress potential spurious warnings
            _channel_cache.purge()

            log("PARENT:Sending Done command to child")
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)
            log(f"PARENT: Join completed with exitcode {process.exitcode}")
            if process.exitcode is None:
                pytest.fail("Process did not terminate")

    @requires_cothread
    def test_on_update_false_false(self, out_records):
        """Test that on_update works correctly for all out records when
        always_update is False and the put'ed value is always different"""
        self.on_update_runner(out_records, False, False)

    @requires_cothread
    def test_on_update_false_true(self, out_records):
        """Test that on_update works correctly for all out records when
        always_update is False and the put'ed value is always the same"""
        self.on_update_runner(out_records, False, True)

    @requires_cothread
    def test_on_update_true_true(self, out_records):
        """Test that on_update works correctly for all out records when
        always_update is True and the put'ed value is always the same"""
        self.on_update_runner(out_records, True, True)

    @requires_cothread
    def test_on_update_true_false(self, out_records):
        """Test that on_update works correctly for all out records when
        always_update is True and the put'ed value is always different"""
        self.on_update_runner(out_records, True, False)



class TestBlocking:
    """Tests related to the Blocking functionality"""

    def check_record_blocking_attributes(self, record):
        """Helper function to assert expected attributes exist for a blocking
        record"""
        assert record._blocking is True
        assert record._callback != 0

    def test_blocking_creates_attributes(self):
        """Test that setting the blocking flag on record creation creates the
        expected attributes"""
        ao1 = builder.aOut("OUTREC1", blocking=True)
        self.check_record_blocking_attributes(ao1)

        ao2 = builder.aOut("OUTREC2", blocking=False)
        assert ao2._blocking is False

    def test_blocking_global_flag_creates_attributes(self):
        """Test that the global blocking flag creates the expected attributes"""
        SetBlocking(True)
        bo1 = builder.boolOut("OUTREC1")
        self.check_record_blocking_attributes(bo1)

        SetBlocking(False)
        bo2 = builder.boolOut("OUTREC2")
        assert bo2._blocking is False

        bo3 = builder.boolOut("OUTREC3", blocking=True)
        self.check_record_blocking_attributes(bo3)

    def test_blocking_returns_old_state(self):
        """Test that SetBlocking returns the previously set value"""
        old_val = SetBlocking(True)
        assert old_val is False  # Default is False

        old_val = SetBlocking(False)
        assert old_val is True

        # Test it correctly maintains state when passed the current value
        old_val = SetBlocking(False)
        assert old_val is False
        old_val = SetBlocking(False)
        assert old_val is False

    def blocking_test_func(self, device_name, conn):

        builder.SetDeviceName(device_name)

        count_rec = builder.longIn("BLOCKING-COUNTER", initial_value=0)

        async def blocking_update_func(new_val):
            """A function that will block for some time"""
            log("CHILD: blocking_update_func starting")
            await asyncio.sleep(0.5)
            log("CHILD: Finished sleep!")
            completed_count = count_rec.get() + 1
            count_rec.set(completed_count)
            log(
                "CHILD: blocking_update_func finished, completed ",
                completed_count
            )

        builder.longOut(
            "BLOCKING-REC",
            on_update=blocking_update_func,
            always_update=True,
            blocking=True
        )


        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        conn.send("R")  # "Ready"

        log("CHILD: Sent R over Connection to Parent")

        # Keep process alive while main thread runs CAGET
        if conn.poll(TIMEOUT):
            val = conn.recv()
            assert val == "D", "Did not receive expected Done character"

        log("CHILD: Received exit command, child exiting")

    @requires_cothread
    def test_blocking_single_thread_multiple_calls(self):
        """Test that a blocking record correctly causes multiple caputs from
        a single thread to wait for the expected time"""
        ctx = get_multiprocessing_context()

        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.blocking_test_func,
            args=(device_name, child_conn),
        )

        process.start()

        log("PARENT: Child started, waiting for R command")

        from cothread.catools import caget, caput, _channel_cache

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")

            log("PARENT: received R command")

            # Suppress potential spurious warnings
            _channel_cache.purge()

            # Track number of puts sent
            count = 1
            MAX_COUNT = 4

            log("PARENT: begining While loop")

            while count <= MAX_COUNT:
                put_ret = caput(
                    device_name + ":BLOCKING-REC",
                    5,  # Arbitrary value
                    wait=True,
                    timeout=TIMEOUT
                )
                assert put_ret.ok, f"caput did not succeed: {put_ret.errorcode}"

                log(f"PARENT: completed caput with count {count}")

                count += 1

            log("PARENT: Getting value from counter")

            ret_val = caget(
                device_name + ":BLOCKING-COUNTER",
                timeout=TIMEOUT,
            )
            assert ret_val.ok, \
                f"caget did not succeed: {ret_val.errorcode}, {ret_val}"

            log(f"PARENT: Received val from COUNTER: {ret_val}")

            assert ret_val == MAX_COUNT

        finally:
            # Suppress potential spurious warnings
            _channel_cache.purge()

            log("PARENT: Sending Done command to child")
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)
            log(f"PARENT: Join completed with exitcode {process.exitcode}")
            if process.exitcode is None:
                pytest.fail("Process did not terminate")

    @pytest.mark.asyncio
    async def test_blocking_multiple_threads(self):
        """Test that a blocking record correctly causes caputs from multiple
        threads to wait for the expected time"""
        ctx = get_multiprocessing_context()
        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.blocking_test_func,
            args=(device_name, child_conn),
        )

        process.start()

        log("PARENT: Child started, waiting for R command")

        from aioca import caget, caput

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")

            log("PARENT: received R command")

            MAX_COUNT = 4

            async def query_record(index):
                log("SPAWNED: beginning blocking caput ", index)
                await caput(
                        device_name + ":BLOCKING-REC",
                        5,  # Arbitrary value
                        wait=True,
                        timeout=TIMEOUT
                    )
                log("SPAWNED: caput complete ", index)

            queries = [query_record(i) for i in range(MAX_COUNT)] * MAX_COUNT

            log("PARENT: Gathering list of queries")

            await asyncio.gather(*queries)

            log("PARENT: Getting value from counter")

            ret_val = await caget(
                device_name + ":BLOCKING-COUNTER",
                timeout=TIMEOUT,
            )
            assert ret_val.ok, \
                f"caget did not succeed: {ret_val.errorcode}, {ret_val}"

            log(f"PARENT: Received val from COUNTER: {ret_val}")

            assert ret_val == MAX_COUNT

        finally:
            # Clear the cache before stopping the IOC stops
            # "channel disconnected" error messages
            aioca_cleanup()

            log("PARENT: Sending Done command to child")
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)
            log(f"PARENT: Join completed with exitcode {process.exitcode}")
            if process.exitcode is None:
                pytest.fail("Process did not terminate")

class TestGetSetField:
    """Tests related to get_field and set_field on records"""

    test_result_rec = "TestResult"

    def test_set_field_before_init_fails(self):
        """Test that calling set_field before iocInit() raises an exception"""

        ao = builder.aOut("testAOut")

        with pytest.raises(AssertionError) as e:
            ao.set_field("EGU", "Deg")

        assert "set_field may only be called after iocInit" in str(e.value)

    def test_get_field_before_init_fails(self):
        """Test that calling get_field before iocInit() raises an exception"""

        ao = builder.aOut("testAOut")

        with pytest.raises(AssertionError) as e:
            ao.get_field("EGU")

        assert "get_field may only be called after iocInit" in str(e.value)

    def get_set_test_func(self, device_name, conn):
        """Run an IOC and do simple get_field/set_field calls"""

        builder.SetDeviceName(device_name)

        lo = builder.longOut("TestLongOut", EGU="unset", DRVH=12)

        # Record to indicate success/failure
        bi = builder.boolIn(self.test_result_rec, ZNAM="FAILED", ONAM="SUCCESS")

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        conn.send("R")  # "Ready"

        log("CHILD: Sent R over Connection to Parent")

        # Set and then get the EGU field
        egu = "TEST"
        lo.set_field("EGU", egu)
        log("CHILD: set_field successful")
        readback_egu = lo.get_field("EGU")
        log(f"CHILD: get_field returned {readback_egu}")
        assert readback_egu == egu, \
            f"EGU field was not {egu}, was {readback_egu}"

        log("CHILD: assert passed")

        # Test completed, report to listening camonitor
        bi.set(True)

        # Keep process alive while main thread works.
        while (True):
            if conn.poll(TIMEOUT):
                val = conn.recv()
                if val == "D":  # "Done"
                    break

        log("CHILD: Received exit command, child exiting")


    @pytest.mark.asyncio
    async def test_get_set(self):
        """Test a simple set_field/get_field is successful"""
        ctx = get_multiprocessing_context()
        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.get_set_test_func,
            args=(device_name, child_conn),
        )

        process.start()

        log("PARENT: Child started, waiting for R command")

        from aioca import camonitor

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")

            log("PARENT: received R command")

            queue = asyncio.Queue()
            record = device_name + ":" + self.test_result_rec
            monitor = camonitor(record, queue.put)

            log(f"PARENT: monitoring {record}")
            new_val = await asyncio.wait_for(queue.get(), TIMEOUT)
            log(f"PARENT: new_val is {new_val}")
            assert new_val == 1, \
                f"Test failed, value was not 1(True), was {new_val}"


        finally:
            monitor.close()
            # Clear the cache before stopping the IOC stops
            # "channel disconnected" error messages
            aioca_cleanup()

            log("PARENT: Sending Done command to child")
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)
            log(f"PARENT: Join completed with exitcode {process.exitcode}")
            if process.exitcode is None:
                pytest.fail("Process did not terminate")

    def get_set_too_long_value(self, device_name, conn):
        """Run an IOC and deliberately call set_field with a too-long value"""

        builder.SetDeviceName(device_name)

        lo = builder.longOut("TestLongOut", EGU="unset", DRVH=12)

        # Record to indicate success/failure
        bi = builder.boolIn(self.test_result_rec, ZNAM="FAILED", ONAM="SUCCESS")

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        conn.send("R")  # "Ready"

        log("CHILD: Sent R over Connection to Parent")

        # Set a too-long value and confirm it reports an error
        try:
            lo.set_field("EGU", "ThisStringIsFarTooLongToFitIntoTheEguField")
        except ValueError as e:
            # Expected error, report success to listening camonitor
            assert "byte string too long" in e.args[0]
            bi.set(True)

        # Keep process alive while main thread works.
        while (True):
            if conn.poll(TIMEOUT):
                val = conn.recv()
                if val == "D":  # "Done"
                    break

        log("CHILD: Received exit command, child exiting")

    @pytest.mark.asyncio
    async def test_set_too_long_value(self):
        """Test that set_field with a too-long value raises the expected
        error"""
        ctx = get_multiprocessing_context()
        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.get_set_too_long_value,
            args=(device_name, child_conn),
        )

        process.start()

        log("PARENT: Child started, waiting for R command")

        from aioca import camonitor

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")

            log("PARENT: received R command")

            queue = asyncio.Queue()
            record = device_name + ":" + self.test_result_rec
            monitor = camonitor(record, queue.put)

            log(f"PARENT: monitoring {record}")
            new_val = await asyncio.wait_for(queue.get(), TIMEOUT)
            log(f"PARENT: new_val is {new_val}")
            assert new_val == 1, \
                f"Test failed, value was not 1(True), was {new_val}"

        finally:
            monitor.close()
            # Clear the cache before stopping the IOC stops
            # "channel disconnected" error messages
            aioca_cleanup()

            log("PARENT: Sending Done command to child")
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)
            log(f"PARENT: Join completed with exitcode {process.exitcode}")
            if process.exitcode is None:
                pytest.fail("Process did not terminate")


class TestRecursiveSet:
    """Tests related to recursive set() calls. See original issue here:
    https://github.com/dls-controls/pythonSoftIOC/issues/119"""

    recursive_record_name = "RecursiveLongOut"

    def recursive_set_func(self, device_name, conn):
        from cothread import Event

        def useless_callback(value):
            log("CHILD: In callback ", value)
            useless_pv.set(0)
            log("CHILD: Exiting callback")

        def go_away(*args):
            log("CHILD: received exit signal ", args)
            event.Signal()

        builder.SetDeviceName(device_name)


        useless_pv = builder.aOut(
            self.recursive_record_name,
            initial_value=0,
            on_update=useless_callback
        )
        event = Event()
        builder.Action("GO_AWAY", on_update = go_away)

        builder.LoadDatabase()
        softioc.iocInit()

        conn.send("R")  # "Ready"
        log("CHILD: Sent R over Connection to Parent")

        log("CHILD: About to wait")
        event.Wait()
        log("CHILD: Exiting")

    @requires_cothread
    @pytest.mark.asyncio
    async def test_recursive_set(self):
        """Test that recursive sets do not cause a deadlock"""
        ctx = get_multiprocessing_context()
        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.recursive_set_func,
            args=(device_name, child_conn),
        )

        process.start()

        log("PARENT: Child started, waiting for R command")

        from aioca import caput, camonitor

        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")
            log("PARENT: received R command")

            record = device_name + ":" + self.recursive_record_name

            log(f"PARENT: monitoring {record}")
            queue = asyncio.Queue()
            monitor = camonitor(record, queue.put, all_updates=True)

            log("PARENT: Beginning first wait")

            # Expected initial state
            new_val = await asyncio.wait_for(queue.get(), TIMEOUT)
            log(f"PARENT: initial new_val: {new_val}")
            assert new_val == 0

            # Try a series of caput calls, to maximise chance to trigger
            # the deadlock
            i = 1
            while i < 500:
                log(f"PARENT: begin loop with i={i}")
                await caput(record, i)
                new_val = await asyncio.wait_for(queue.get(), 1)
                assert new_val == i
                new_val = await asyncio.wait_for(queue.get(), 1)
                assert new_val == 0  # .set() should reset value
                i += 1

            # Signal the IOC to cleanly shut down
            await caput(device_name + ":" + "GO_AWAY", 1)

        except asyncio.TimeoutError as e:
            raise asyncio.TimeoutError(
                f"IOC did not send data back - loop froze on iteration {i} "
                "- it has probably hung/deadlocked."
            ) from e

        finally:
            monitor.close()
            # Clear the cache before stopping the IOC stops
            # "channel disconnected" error messages
            aioca_cleanup()

            process.join(timeout=TIMEOUT)
            log(f"PARENT: Join completed with exitcode {process.exitcode}")
            if process.exitcode is None:
                process.terminate()
                pytest.fail("Process did not finish cleanly, terminating")
