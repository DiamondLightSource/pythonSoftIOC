import multiprocessing
import numpy
import os
import pytest
import asyncio

from conftest import requires_cothread, _clear_records, enable_code_coverage

from softioc import asyncio_dispatcher, builder, softioc

# Test file for miscellaneous tests related to records

# Test parameters
DEVICE_NAME = "RECORD-TESTS"
TIMEOUT = 5  # Seconds

def test_records(tmp_path, clear_records):
    # Ensure we definitely unload all records that may be hanging over from
    # previous tests, then create exactly one instance of expected records.
    from sim_records import create_records
    _clear_records()
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


def test_DISP_defaults_on():
    """Test that all IN record types have DISP=1 set by default"""
    in_records = [
        builder.aIn,
        builder.boolIn,
        builder.longIn,
        builder.mbbIn,
        builder.stringIn,
        builder.WaveformIn,
    ]

    record_counter = 0

    for creation_func in in_records:
        kwargs = {}
        record_counter += 1
        record_name = "DISP" + str(record_counter)

        if creation_func == builder.WaveformIn:
            kwargs = {"length": 1}

        record = creation_func(record_name, **kwargs)

        # Note: DISP attribute won't exist if field not specified
        assert record.DISP.Value() == 1


def test_DISP_can_be_overridden():
    """Test that DISP can be forced off for In records"""

    record = builder.longIn("DISP-OFF", DISP=0)
    # Note: DISP attribute won't exist if field not specified
    assert record.DISP.Value() == 0

def test_waveform_disallows_zero_length(clear_records):
    """Test that WaveformIn/Out records throw an exception when being
    initialized with a zero length array"""
    with pytest.raises(AssertionError):
        builder.WaveformIn("W_IN", [])
    with pytest.raises(AssertionError):
        builder.WaveformOut("W_OUT", [])

def test_waveform_disallows_too_long_values(clear_records):
    """Test that Waveform and longString records throw an exception when
    an overlong value is written"""
    w_in = builder.WaveformIn("W_IN", [1, 2, 3])
    w_out = builder.WaveformOut("W_OUT", [1, 2, 3])

    ls_in = builder.longStringIn("LS_IN", initial_value="ABC")
    ls_out = builder.longStringOut("LS_OUT", initial_value="ABC")

    with pytest.raises(AssertionError):
        w_in.set([1, 2, 3, 4])
    with pytest.raises(AssertionError):
        w_out.set([1, 2, 3, 4])
    with pytest.raises(AssertionError):
        ls_in.set("ABCD")
    with pytest.raises(AssertionError):
        ls_out.set("ABCD")

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

    def validate_ioc_test_func(self, record_func, queue, validate_pass: bool):
        """Start the IOC with the specified validate method"""

        builder.SetDeviceName(DEVICE_NAME)

        kwarg = {}
        if record_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        kwarg.update(
            {
                "validate": self.validate_always_pass
                if validate_pass
                else self.validate_always_fail
            }
        )

        record_func("VALIDATE-RECORD", **kwarg)

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        queue.put("IOC ready")

        # Keep process alive while main thread runs CAGET
        queue.get(timeout=5)

    def validate_test_runner(
            self,
            creation_func,
            new_value,
            expected_value,
            validate_pass: bool):

        queue = multiprocessing.Queue()

        enable_code_coverage()

        process = multiprocessing.Process(
            target=self.validate_ioc_test_func,
            args=(creation_func, queue, validate_pass),
        )

        process.start()

        try:
            queue.get(timeout=5)  # Get the expected IOC initialised message

            from cothread.catools import caget, caput, _channel_cache

            # See other places in this file for why we call it
            _channel_cache.purge()

            kwargs = {}
            if creation_func in [builder.longStringIn, builder.longStringOut]:
                from cothread.dbr import DBR_CHAR_STR
                kwargs.update({"datatype": DBR_CHAR_STR})

            put_ret = caput(
                DEVICE_NAME + ":" + "VALIDATE-RECORD",
                new_value,
                wait=True,
                **kwargs,
            )
            assert put_ret.ok, "caput did not succeed"

            ret_val = caget(
                DEVICE_NAME + ":" + "VALIDATE-RECORD",
                timeout=3,
                **kwargs
            )

            if creation_func in [builder.WaveformOut, builder.WaveformIn]:
                assert numpy.array_equal(ret_val, expected_value)
            else:
                assert ret_val == expected_value

        finally:
            queue.put("EXIT")
            process.join(timeout=3)


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
