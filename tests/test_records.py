import multiprocessing
from typing import List
import numpy
import os
import pytest
import sys
import asyncio
import logging

from enum import Enum
from math import isnan, inf, nan

# Must import softioc before epicsdbbuilder
from softioc.device_core import RecordLookup
from softioc import asyncio_dispatcher, builder, softioc

from epicsdbbuilder import ResetRecords

from softioc.pythonSoftIoc import RecordWrapper

requires_cothread = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Cothread doesn't work on windows"
)


# Test parameters
DEVICE_NAME = "SOFT-IOC-TESTS"
TIMEOUT = 5  # Seconds

VERY_LONG_STRING = "This is a fairly long string, the kind that someone " \
    "might think to put into a record that can theoretically hold a huge " \
    "string and so lets test it and prove that shall we?"


def _clear_records():
    # Remove any records created at epicsdbbuilder layer
    ResetRecords()
    # And at pythonSoftIoc level
    # TODO: Remove this hack and use use whatever comes out of
    # https://github.com/dls-controls/pythonSoftIOC/issues/56
    RecordLookup._RecordDirectory.clear()


@pytest.fixture
def clear_records():
    """Fixture to delete all records before and after a test."""
    _clear_records()
    yield
    _clear_records()


def record_func_names(fixture_value):
    """Provide a nice name for the record_func fixture"""
    return fixture_value.__name__


@pytest.fixture(
    params=[
        builder.aIn,
        builder.aOut,
        builder.longIn,
        builder.longOut,
        builder.boolIn,
        builder.boolOut,
        builder.Action,
        builder.stringIn,
        builder.stringOut,
        builder.mbbIn,
        builder.mbbOut,
        builder.WaveformIn,
        builder.WaveformOut,
        builder.longStringIn,
        builder.longStringOut,
    ],
    ids=record_func_names,
)
def record_func(request):
    """The list of record creation functions"""
    return request.param

# A list of all In records, used to filter out various tests
in_records = [
    builder.aIn,
    builder.boolIn,
    builder.longIn,
    builder.mbbIn,
    builder.stringIn,
    builder.WaveformIn,
    builder.longStringIn,
]

def record_values_names(fixture_value):
    """Provide a nice name for the tests in the record_values fixture"""
    return (
        fixture_value[1].__name__
        + "-"
        + type(fixture_value[2]).__name__
        + "-"
        + str(fixture_value[3])
    )


record_values_list = [
    ("aIn_float", builder.aIn, 5.5, 5.5, float),
    ("aOut_float", builder.aOut, 5.5, 5.5, float),
    ("aIn_int", builder.aIn, 3, 3.0, float),
    ("aOut_int", builder.aOut, 3, 3.0, float),
    ("aIn_inf", builder.aIn, inf, inf, float),
    ("aOut_inf", builder.aOut, inf, inf, float),
    ("aIn_neginf", builder.aIn, -inf, -inf, float),
    ("aOut_neginf", builder.aOut, -inf, -inf, float),
    ("aIn_nan", builder.aIn, nan, nan, float),
    ("aOut_nan", builder.aOut, nan, nan, float),
    ("longIn_int", builder.longIn, 5, 5, int),
    ("longOut_int", builder.longOut, 5, 5, int),
    ("boolIn_int", builder.boolIn, 1, 1, int),
    ("boolOut_int", builder.boolOut, 1, 1, int),
    ("boolIn_true", builder.boolIn, True, 1, int),
    ("boolOut_true", builder.boolOut, True, 1, int),
    ("boolIn_false", builder.boolIn, False, 0, int),
    ("boolOut_false", builder.boolOut, False, 0, int),
    ("Action_int", builder.Action, 1, 1, int),
    ("Action_true", builder.Action, True, 1, int),
    ("Action_false", builder.Action, False, 0, int),
    ("mbbIn_int", builder.mbbIn, 1, 1, int),
    ("mbbOut_int", builder.mbbOut, 1, 1, int),
    ("strIn_abc", builder.stringIn, "abc", "abc", str),
    ("strOut_abc", builder.stringOut, "abc", "abc", str),
    ("strIn_empty", builder.stringIn, "", "", str),
    ("strOut_empty", builder.stringOut, "", "", str),
    ("strin_utf8", builder.stringIn, "%a€b", "%a€b", str),  # Valid UTF-8
    ("strOut_utf8", builder.stringOut, "%a€b", "%a€b", str),  # Valid UTF-8
    (
        "wIn_list_int",
        builder.WaveformIn,
        [1, 2, 3],
        numpy.array([1, 2, 3], dtype=numpy.int32),
        numpy.ndarray,
    ),
    (
        "wOut_list_int",
        builder.WaveformOut,
        [1, 2, 3],
        numpy.array([1, 2, 3], dtype=numpy.int32),
        numpy.ndarray,
    ),
    (
        "wIn_list_float",
        builder.WaveformIn,
        [1.5, 2.6, 3.7],
        numpy.array([1.5, 2.6, 3.7], dtype=numpy.float64),
        numpy.ndarray,
    ),
    (
        "wOut_list_float",
        builder.WaveformOut,
        [1.5, 2.6, 3.7],
        numpy.array([1.5, 2.6, 3.7], dtype=numpy.float64),
        numpy.ndarray,
    ),
    (
        "wIn_int",
        builder.WaveformIn,
        567,
        numpy.array([567.], dtype=numpy.float64),
        numpy.ndarray,
    ),
    (
        "wOut_int",
        builder.WaveformOut,
        567,
        numpy.array([567.], dtype=numpy.float64),
        numpy.ndarray,
    ),
    (
        "wIn_float",
        builder.WaveformIn,
        12.345,
        numpy.array([12.345], dtype=numpy.float64),
        numpy.ndarray,
    ),
    (
        "wOut_float",
        builder.WaveformOut,
        12.345,
        numpy.array([12.345], dtype=numpy.float64),
        numpy.ndarray,
    ),
    (
        "wIn_bytes",
        builder.WaveformIn,
        b"HELLO\0WORLD",
        numpy.array(
            [72, 69, 76, 76, 79, 0, 87, 79, 82, 76, 68], dtype=numpy.uint8
        ),
        numpy.ndarray,
    ),
    (
        "wOut_bytes",
        builder.WaveformOut,
        b"HELLO\0WORLD",
        numpy.array(
            [72, 69, 76, 76, 79, 0, 87, 79, 82, 76, 68], dtype=numpy.uint8
        ),
        numpy.ndarray,
    ),
    (
        "longStringIn_str",
        builder.longStringIn,
        "ABC",
        "ABC",
        str,
    ),
    (
        "longStringOut_str",
        builder.longStringOut,
        "ABC",
        "ABC",
        str,
    ),
    (
        "longStringIn_long_str",
        builder.longStringIn,
        VERY_LONG_STRING,
        VERY_LONG_STRING,
        str,
    ),
    (
        "longStringOut_long_str",
        builder.longStringOut,
        VERY_LONG_STRING,
        VERY_LONG_STRING,
        str,
    ),
    (
        "longStringIn_unicode",
        builder.longStringIn,
        "%a€b",
        "%a€b",
        str
    ),
    (
        "longStringOut_unicode",
        builder.longStringOut,
        "%a€b",
        "%a€b",
        str
    ),
]


@pytest.fixture(params=record_values_list, ids=record_values_names)
def record_values(request):
    """A list of parameters for record value setting/getting tests.

    Fields are:
    - Record builder function
    - Input value passed to .set()/initial_value/caput
    - Expected output value after doing .get()/caget
    - Expected type of the output value from .get()/caget"""
    return request.param  # One item from the params list


def test_records(tmp_path):
    import sim_records

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


def record_value_asserts(
    creation_func, actual_value, expected_value, expected_type
):
    """Asserts that the expected value and expected type are matched with
    the actual value. Handles both scalar and waveform data"""
    try:
        if type(expected_value) == float and isnan(expected_value):
            assert isnan(actual_value)  # NaN != Nan, so needs special case
        elif creation_func in [builder.WaveformOut, builder.WaveformIn]:
            assert numpy.array_equal(actual_value, expected_value)
            assert type(actual_value) == expected_type
        else:
            assert actual_value == expected_value
            assert type(actual_value) == expected_type
    except AssertionError as e:
        msg = (
            "Failed with parameters: "
            + str(creation_func)
            + ", "
            + str(actual_value)
            + ", "
            + str(expected_value)
            + ", "
            + str(expected_type)
        )
        # Add the parameters into the exception message. Seems to be the
        # cleanest place to add it, as doing a print() or a logging.error()
        # both cause the message to appear in a separate section of the pytest
        # results, which can be difficult to spot
        e.args += (msg,)
        raise e


class SetValueEnum(Enum):
    """Enum to control when and how the record's value should be set"""

    INITIAL_VALUE = 1
    SET_BEFORE_INIT = 2
    SET_AFTER_INIT = 3
    NO_SET = 4
    CAPUT = 5


class GetValueEnum(Enum):
    """Enum to control whether values are retrieved using .get() or caget()"""

    GET = 1
    CAGET = 2


def run_ioc(record_configurations: list, conn, set_enum, get_enum):
    """Creates a record and starts the IOC. `initial_value` will be set on
    the record at different times based on the `set_enum` parameter."""

    builder.SetDeviceName(DEVICE_NAME)

    records: List[RecordWrapper] = []

    # Create records from the given list
    for configuration in record_configurations:
        kwarg = {}

        (
            record_name,
            creation_func,
            initial_value,
            expected_value,
            expected_type,
        ) = configuration

        if set_enum == SetValueEnum.INITIAL_VALUE:
            kwarg.update({"initial_value": initial_value})
        elif creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation
            # Related to this issue:
            # https://github.com/dls-controls/pythonSoftIOC/issues/37

        out_rec = creation_func(record_name, **kwarg)

        if set_enum == SetValueEnum.SET_BEFORE_INIT:
            out_rec.set(initial_value)

        records.append(out_rec)

    dispatcher = asyncio_dispatcher.AsyncioDispatcher()
    builder.LoadDatabase()
    softioc.iocInit(dispatcher)
    conn.send("IOC started")

    # Record list and record config list should always be in line
    for record, configuration in zip(records, record_configurations):
        (
            record_name,
            creation_func,
            initial_value,
            expected_value,
            expected_type,
        ) = configuration

        if set_enum == SetValueEnum.SET_AFTER_INIT:
            record.set(initial_value)

    for record in records:
        if get_enum == GetValueEnum.GET:
            conn.send(record.get())
            # Some tests do a caput and require another .get()
            if set_enum == SetValueEnum.CAPUT:
                if conn.poll(TIMEOUT):
                    val = conn.recv()
                    if val is not None:
                        conn.send(record.get())

    conn.close()

    # Keep process alive while main thread works.
    # This is most applicable to CAGET tests.
    asyncio.run_coroutine_threadsafe(
        asyncio.sleep(TIMEOUT), dispatcher.loop
    ).result()


def run_test_function(
    record_configurations: list, set_enum: SetValueEnum, get_enum: GetValueEnum
):
    """Run the test function using multiprocessing and check returned value is
    expected value. set_enum and get_enum determine when the record's value is
    set and how the value is retrieved, respectively."""

    parent_conn, child_conn = multiprocessing.Pipe()

    ioc_process = multiprocessing.Process(
        target=run_ioc,
        args=(record_configurations, child_conn, set_enum, get_enum),
    )

    ioc_process.start()

    # Wait for message that IOC has started
    if parent_conn.poll(TIMEOUT):
        parent_conn.recv()
    else:
        pytest.fail("IOC process did not start before TIMEOUT expired")

    try:
        # Cannot do these imports before the subprocess starts, as cothread
        # isn't threadsafe (in the way we require)
        from cothread import Yield
        from cothread.catools import caget, caput, _channel_cache
        from cothread.dbr import DBR_CHAR_STR

        # cothread remembers connected IOCs. As we potentially restart the same
        # named IOC multiple times, we have to purge the cache else the
        # result from caget/caput cache would be a DisconnectError during the
        # second test
        _channel_cache.purge()

        for configuration in record_configurations:
            (
                record_name,
                creation_func,
                initial_value,
                expected_value,
                expected_type,
            ) = configuration

            # Infer some required keywords from parameters
            kwargs = {}
            put_kwarg = {}
            if creation_func in [builder.longStringIn, builder.longStringOut]:
                kwargs.update({"datatype": DBR_CHAR_STR})

            if (creation_func in [builder.WaveformIn, builder.WaveformOut]
                    and type(initial_value) is bytes):
                # There's a bug in caput that means DBR_CHAR_STR doesn't
                # truncate the array of the target record, meaning .get()
                # returns all NELM rather than just NORD elements. Instead we
                # encode the data ourselves
                initial_value = numpy.frombuffer(
                    initial_value, dtype = numpy.uint8)

            if set_enum == SetValueEnum.CAPUT:
                if get_enum == GetValueEnum.GET:
                    if parent_conn.poll(TIMEOUT):
                        parent_conn.recv()
                    else:
                        pytest.fail("IOC did not provide initial record value")
                caput(
                    DEVICE_NAME + ":" + record_name,
                    initial_value,
                    wait=True,
                    **kwargs,
                    **put_kwarg,
                )

                if get_enum == GetValueEnum.GET:
                    parent_conn.send("Do another get!")
                # Ensure IOC process has time to execute.
                # I saw failures on MacOS where it appeared the IOC had not
                # processed the put'ted value as the caget returned the same
                # value as was originally passed in.
                Yield(timeout=TIMEOUT)

            if get_enum == GetValueEnum.GET:
                if parent_conn.poll(TIMEOUT):
                    rec_val = parent_conn.recv()
                else:
                    pytest.fail("IOC did not provide record value in queue")
            else:
                rec_val = caget(
                    DEVICE_NAME + ":" + record_name,
                    timeout=TIMEOUT,
                    **kwargs,
                )
                # '+' operator used to convert cothread's types into Python
                # native types e.g. "+ca_int" -> int
                rec_val = +rec_val

                if (
                    creation_func in [builder.WaveformOut, builder.WaveformIn]
                    and expected_value.dtype in [numpy.float64, numpy.int32]
                ):
                    print(
                        "caget cannot distinguish between a waveform with 1"
                        "element and a scalar value, and so always returns a "
                        "scalar. Therefore we skip this check.")
                    continue


            record_value_asserts(
                creation_func, rec_val, expected_value, expected_type
            )
    finally:
        # Purge cache to suppress spurious "IOC disconnected" exceptions
        _channel_cache.purge()

        ioc_process.terminate()
        ioc_process.join(timeout=TIMEOUT)
        if ioc_process.exitcode is None:
            pytest.fail("Process did not terminate")


def skip_long_strings(record_values):
    if (
        record_values[0] in [builder.stringIn, builder.stringOut]
        and len(record_values[1]) > 40
    ):
        pytest.skip("CAPut blocks strings > 40 characters.")


class TestGetValue:
    """Tests that use .get() to check whether values applied with .set(),
    initial_value, or caput return the expected value"""

    def test_value_pre_init_set(self, clear_records, record_values):
        """Test that records provide the expected values on get calls when using
        .set() and .get() before IOC initialisation occurs"""

        (
            record_name,
            creation_func,
            initial_value,
            expected_value,
            expected_type,
        ) = record_values

        kwarg = {}
        if creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        out_rec = creation_func(record_name, **kwarg)
        out_rec.set(initial_value)

        record_value_asserts(
            creation_func, out_rec.get(), expected_value, expected_type
        )

    def test_value_pre_init_initial_value(self, clear_records, record_values):
        """Test that records provide the expected values on get calls when using
        initial_value and .get() before IOC initialisation occurs"""

        (
            record_name,
            creation_func,
            initial_value,
            expected_value,
            expected_type,
        ) = record_values

        out_rec = creation_func(record_name, initial_value=initial_value)

        record_value_asserts(
            creation_func, out_rec.get(), expected_value, expected_type
        )

    @requires_cothread
    def test_value_post_init_set(self):
        """Test that records provide the expected values on get calls when using
        .set() before IOC initialisation and .get() after initialisation"""
        run_test_function(
            record_values_list, SetValueEnum.SET_BEFORE_INIT, GetValueEnum.GET
        )

    @requires_cothread
    def test_value_post_init_initial_value(self):
        """Test that records provide the expected values on get calls when using
        initial_value during record creation and .get() after IOC initialisation
        """
        run_test_function(
            record_values_list, SetValueEnum.INITIAL_VALUE, GetValueEnum.GET
        )

    @requires_cothread
    def test_value_post_init_set_after_init(self):
        """Test that records provide the expected values on get calls when using
        .set() and .get() after IOC initialisation"""
        run_test_function(
            record_values_list, SetValueEnum.SET_AFTER_INIT, GetValueEnum.GET
        )

    @requires_cothread
    def test_value_post_init_caput(self):
        """Test that records provide the expected values on get calls when using
        caput and .get() after IOC initialisation"""

        # Various conditions mean we cannot use the entire list of cases
        filtered_list = []
        for item in record_values_list:
            if (
                item[1] in [builder.stringIn, builder.stringOut]
                and len(item[2]) > 40
            ):
                # caput blocks strings longer than 40 characters
                continue

            if item[1] not in in_records:
                # In records block caput
                filtered_list.append(item)

        run_test_function(filtered_list, SetValueEnum.CAPUT, GetValueEnum.GET)


@requires_cothread
class TestCagetValue:
    """Tests that use Caget to check whether values applied with .set(),
    initial_value, or caput return the expected value"""

    def test_value_post_init_set(self):
        """Test that records provide the expected values on get calls when using
        .set() before IOC initialisation and caget after initialisation"""

        # Various conditions mean we cannot use the entire list of cases
        filtered_list = []
        for item in record_values_list:
            # .set() on In records doesn't update correctly.
            # pythonSoftIOC issue #67
            if item[1] not in in_records:
                filtered_list.append(item)

        run_test_function(
            filtered_list, SetValueEnum.SET_BEFORE_INIT, GetValueEnum.CAGET
        )

    @requires_cothread
    def test_value_post_init_initial_value(self):
        """Test that records provide the expected values on get calls when using
        initial_value during record creation and caget after IOC initialisation
        """

        run_test_function(
            record_values_list, SetValueEnum.INITIAL_VALUE, GetValueEnum.CAGET
        )

    @requires_cothread
    def test_value_post_init_set_after_init(self):
        """Test that records provide the expected values on get calls when using
        .set() and caget after IOC initialisation"""

        run_test_function(
            record_values_list, SetValueEnum.SET_AFTER_INIT, GetValueEnum.CAGET
        )

    def test_value_post_init_caput(self):
        """Test that records provide the expected values on get calls when using
        .set() before IOC initialisation and caget after initialisation"""

        # Various conditions (e.g.) mean we cannot use the entire list of cases
        filtered_list = []
        for item in record_values_list:
            # In records block caputs
            if item[1] not in in_records:
                filtered_list.append(item)

        run_test_function(filtered_list, SetValueEnum.CAPUT, GetValueEnum.CAGET)


default_values_list = [
    ("default_aOut", builder.aOut, None, 0.0, float),
    ("default_aIn", builder.aIn, None, 0.0, float),
    ("default_longOut", builder.longOut, None, 0, int),
    ("default_longIn", builder.longIn, None, 0, int),
    ("default_boolOut", builder.boolOut, None, 0, int),
    ("default_boolIn", builder.boolIn, None, 0, int),
    ("default_Action", builder.Action, None, 0, int),
    ("default_stringOut", builder.stringOut, None, "", str),
    ("default_stringIn", builder.stringIn, None, "", str),
    ("default_mbbOut", builder.mbbOut, None, 0, int),
    ("default_mbbIn", builder.mbbIn, None, 0, int),
    ("default_wOut", builder.WaveformOut, None, numpy.empty(0), numpy.ndarray),
    ("default_wIn", builder.WaveformIn, None, numpy.empty(0), numpy.ndarray),
    ("default_longStringOut", builder.longStringOut, None, "", str),
    ("default_longStringIn", builder.longStringIn, None, "", str),
]


class TestDefaultValue:
    """Tests related to default values"""

    @pytest.mark.parametrize(
        "creation_func,expected_value,expected_type",
        [
            (builder.aOut, 0.0, float),
            (builder.aIn, 0.0, float),
            (builder.longOut, 0, int),
            (builder.longIn, 0, int),
            (builder.boolOut, 0, int),
            (builder.boolIn, 0, int),
            (builder.Action, 0, int),
            (builder.stringOut, "", str),
            (builder.stringIn, "", str),
            (builder.mbbOut, 0, int),
            (builder.mbbIn, 0, int),
            (builder.WaveformOut, numpy.empty(0), numpy.ndarray),
            (builder.WaveformIn, numpy.empty(0), numpy.ndarray),
            (builder.longStringOut, "", str),
            (builder.longStringIn, "", str),
        ],
    )
    def test_value_default_pre_init(
        self, creation_func, expected_value, expected_type, clear_records
    ):
        """Test that the correct default values are returned from .get() (before
        record initialisation) when no initial_value or .set() is done"""
        # Out records do not have default values until records are initialized

        kwarg = {}
        if creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        out_rec = creation_func("out-record", **kwarg)
        record_value_asserts(
            creation_func, out_rec.get(), expected_value, expected_type
        )

    @requires_cothread
    def test_value_default_post_init(self):
        """Test that records return the expected default value from .get after
        they are initialised, having never had a value set"""

        run_test_function(
            default_values_list, SetValueEnum.NO_SET, GetValueEnum.GET
        )

    @requires_cothread
    def test_value_default_post_init_caget(self):
        """Test that records return the expected default value from CAGet after
        they are initialised, having never had a value set"""

        run_test_function(
            default_values_list, SetValueEnum.NO_SET, GetValueEnum.CAGET
        )


class TestNoneValue:
    """Various tests regarding record value of None"""

    # We expect using None as a value will trigger one of these exceptions
    expected_exceptions = (ValueError, TypeError, AttributeError)


    @pytest.fixture
    def record_func_reject_none(self, record_func):
        """Parameterized fixture for all records that reject None"""
        if record_func in [builder.WaveformIn, builder.WaveformOut]:
            pytest.skip("None is accepted by Waveform records, as numpy "
                        "treats it as NaN")
        return record_func

    def test_value_none_rejected_initial_value(
        self, clear_records, record_func_reject_none
    ):
        """Test setting \"None\" as the initial_value raises an exception"""

        kwarg = {}
        if record_func_reject_none in [
            builder.WaveformIn,
            builder.WaveformOut,
        ]:
            kwarg = {"length": 50}  # Required when no value on creation

        with pytest.raises(self.expected_exceptions):
            record_func_reject_none("SOME-NAME", initial_value=None, **kwarg)

    def test_value_none_rejected_set_before_init(
        self, clear_records, record_func_reject_none
    ):
        """Test that setting \"None\" using .set() raises an exception"""

        kwarg = {}
        if record_func_reject_none in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        with pytest.raises(self.expected_exceptions):
            record = record_func_reject_none("SOME-NAME", **kwarg)
            record.set(None)

    def none_value_test_func(self, record_func, queue):
        """Start the IOC and catch the expected exception"""
        kwarg = {}
        if record_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        record = record_func("SOME-NAME", **kwarg)

        builder.LoadDatabase()
        softioc.iocInit()

        try:
            record.set(None)
        except Exception as e:
            queue.put(e)

        queue.put(Exception("FAIL:Test did not raise exception during .set()"))

    @requires_cothread
    def test_value_none_rejected_set_after_init(self, record_func_reject_none):
        """Test that setting \"None\" using .set() after IOC init raises an
        exception"""
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=self.none_value_test_func,
            args=(record_func_reject_none, queue),
        )

        process.start()

        try:
            exception = queue.get(timeout=5)

            assert isinstance(exception, self.expected_exceptions)
        finally:
            process.terminate()
            process.join(timeout=3)

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

        # Keep process alive while main thread works.
        # This is most applicable to CAGET tests.
        asyncio.run_coroutine_threadsafe(
            asyncio.sleep(TIMEOUT), dispatcher.loop
        ).result()

    def validate_test_runner(
            self,
            creation_func,
            new_value,
            expected_value,
            validate_pass: bool):

        queue = multiprocessing.Queue()
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
            process.terminate()
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
