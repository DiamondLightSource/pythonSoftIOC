import multiprocessing
from typing import List
import numpy
import pytest

from enum import Enum
from math import isnan, inf, nan

from conftest import (
    requires_cothread,
    WAVEFORM_LENGTH,
    log,
    select_and_recv,
    TIMEOUT,
    get_multiprocessing_context
)

from softioc import asyncio_dispatcher, builder, softioc
from softioc.pythonSoftIoc import RecordWrapper

# Test file for anything related to valid record values getting/setting


# Test parameters
DEVICE_NAME = "RECORD-VALUE-TESTS"

# The maximum length string for StringIn/Out records
MAX_LEN_STR = "a 39 char string exactly maximum length"

VERY_LONG_STRING = "This is a fairly long string, the kind that someone " \
    "might think to put into a record that can theoretically hold a huge " \
    "string and so lets test it and prove that shall we?"


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
    ("strIn_39chars", builder.stringIn, MAX_LEN_STR, MAX_LEN_STR, str),
    ("strOut_39chars", builder.stringOut, MAX_LEN_STR, MAX_LEN_STR, str),
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
        "wIn_byte_string_array",
        builder.WaveformIn,
        [b"AB123", b"CD456", b"EF789"],
        ["AB123", "CD456", "EF789"],
        list,
    ),
    (
        "wOut_byte_string_array",
        builder.WaveformOut,
        [b"12AB", b"34CD", b"56EF"],
        ["12AB", "34CD", "56EF"],
        list,
    ),
    (
        "wIn_unicode_string_array",
        builder.WaveformIn,
        ["12€½", "34¾²", "56¹³"],
        ["12€½", "34¾²", "56¹³"],
        list,
    ),
    (
        "wOut_unicode_string_array",
        builder.WaveformOut,
        ["12€½", "34¾²", "56¹³"],
        ["12€½", "34¾²", "56¹³"],
        list,
    ),
    (
        "wIn_string_array",
        builder.WaveformIn,
        ["123abc", "456def", "7890ghi"],
        ["123abc", "456def", "7890ghi"],
        list,
    ),
    (
        "wOut_string_array",
        builder.WaveformOut,
        ["123abc", "456def", "7890ghi"],
        ["123abc", "456def", "7890ghi"],
        list,
    ),
    (
        "wIn_mixed_array_1",
        builder.WaveformIn,
        ["123abc", 456, "7890ghi"],
        ["123abc", "456", "7890ghi"],
        list,
    ),
    (
        "wOut_mixed_array_1",
        builder.WaveformOut,
        ["123abc", 456, "7890ghi"],
        ["123abc", "456", "7890ghi"],
        list,
    ),
    (
        "wIn_mixed_array_2",
        builder.WaveformIn,
        [123, 456, "7890ghi"],
        ["123", "456", "7890ghi"],
        list,
    ),
    (
        "wOut_mixed_array_2",
        builder.WaveformOut,
        [123, 456, "7890ghi"],
        ["123", "456", "7890ghi"],
        list,
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
    - Record name
    - Record builder function
    - Input value passed to .set()/initial_value/caput
    - Expected output value after doing .get()/caget
    - Expected type of the output value from .get()/caget"""
    return request.param  # One item from the params list



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
            kwarg["initial_value"] = initial_value
        elif creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg["length"] = WAVEFORM_LENGTH  # Must specify when no value
            # Related to this issue:
            # https://github.com/dls-controls/pythonSoftIOC/issues/37

        out_rec = creation_func(record_name, **kwarg)

        if set_enum == SetValueEnum.SET_BEFORE_INIT:
            out_rec.set(initial_value)

        records.append(out_rec)

    dispatcher = asyncio_dispatcher.AsyncioDispatcher()
    builder.LoadDatabase()
    softioc.iocInit(dispatcher)
    conn.send("R")  # "Ready"

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
                    if val == "G":
                        conn.send(record.get())
                    else:
                        pytest.fail(f"Received unexpected character {val}")

    # Keep process alive while main thread works.
    # This is most applicable to CAGET tests.
    while (True):
        if conn.poll(TIMEOUT):
            val = conn.recv()
            if val == "D":  # "Done"
                break

def run_test_function(
    record_configurations: list, set_enum: SetValueEnum, get_enum: GetValueEnum
):
    """Run the test function using multiprocessing and check returned value is
    expected value. set_enum and get_enum determine when the record's value is
    set and how the value is retrieved, respectively."""

    def is_valid(configuration):
        """Remove some cases that cannot succeed.
        Waveforms of Strings must have the value specified as initial value."""
        (
            record_name,
            creation_func,
            initial_value,
            expected_value,
            expected_type,
        ) = configuration

        if creation_func in (builder.WaveformIn, builder.WaveformOut):
            if isinstance(initial_value, list) and \
                    any(isinstance(val, (str, bytes)) for val in initial_value):
                if set_enum is not SetValueEnum.INITIAL_VALUE:
                    print(f"Removing {configuration}")
                    return False

        return True

    record_configurations = [
        x for x in record_configurations if is_valid(x)
    ]

    ctx = get_multiprocessing_context()
    parent_conn, child_conn = ctx.Pipe()

    ioc_process = ctx.Process(
        target=run_ioc,
        args=(record_configurations, child_conn, set_enum, get_enum),
    )

    ioc_process.start()


    # Wait for message that IOC has started
    select_and_recv(parent_conn, "R")

    # Cannot do these imports before the subprocess starts, as the subprocess
    # would inherit cothread's internal state which would break things!
    from cothread import Yield
    from cothread.catools import caget, caput, _channel_cache
    from cothread.dbr import DBR_CHAR_STR

    try:
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
                kwargs["datatype"] = DBR_CHAR_STR

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
                    select_and_recv(parent_conn)
                caput(
                    DEVICE_NAME + ":" + record_name,
                    initial_value,
                    wait=True,
                    **kwargs,
                    **put_kwarg,
                )

                if get_enum == GetValueEnum.GET:
                    parent_conn.send("G")  # "Get"

                # Ensure IOC process has time to execute.
                # I saw failures on MacOS where it appeared the IOC had not
                # processed the put'ted value as the caget returned the same
                # value as was originally passed in.
                Yield(timeout=TIMEOUT)

            if get_enum == GetValueEnum.GET:
                rec_val = select_and_recv(parent_conn)
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
                    and hasattr(expected_value, 'dtype')
                    and expected_value.dtype in [numpy.float64, numpy.int32]
                ):
                    log(
                        "caget cannot distinguish between a waveform with 1 "
                        "element and a scalar value, and so always returns a "
                        "scalar. Therefore we skip this check.")
                    continue

                # caget on a waveform of strings will return a numpy array.
                # Must extract it out to a list to match .get()
                if isinstance(rec_val, numpy.ndarray) and len(rec_val) > 1 \
                        and rec_val.dtype.char in ["S", "U"]:
                    rec_val = [s for s in rec_val]

            record_value_asserts(
                creation_func, rec_val, expected_value, expected_type
            )
    finally:
        # Purge cache to suppress spurious "IOC disconnected" exceptions
        _channel_cache.purge()

        parent_conn.send("D")  # "Done"

        ioc_process.join(timeout=TIMEOUT)
        if ioc_process.exitcode is None:
            pytest.fail("Process did not terminate")



class TestGetValue:
    """Tests that use .get() to check whether values applied with .set(),
    initial_value, or caput return the expected value"""

    def test_value_pre_init_set(self, record_values):
        """Test that records provide the expected values on get calls when using
        .set() and .get() before IOC initialisation occurs"""

        (
            record_name,
            creation_func,
            initial_value,
            expected_value,
            expected_type,
        ) = record_values

        if (
            creation_func in [builder.WaveformIn, builder.WaveformOut] and
            isinstance(initial_value, list) and
            any(isinstance(s, (str, bytes)) for s in initial_value)
        ):
            pytest.skip("Cannot .set() a list of strings to a waveform, must"
                        "initially specify using initial_value or FTVL")

        kwarg = {}
        if creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

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

        run_test_function(
            record_values_list, SetValueEnum.SET_BEFORE_INIT, GetValueEnum.CAGET
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
        self, creation_func, expected_value, expected_type
    ):
        """Test that the correct default values are returned from .get() (before
        record initialisation) when no initial_value or .set() is done"""
        # Out records do not have default values until records are initialized

        kwarg = {}
        if creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

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
        self, record_func_reject_none
    ):
        """Test setting \"None\" as the initial_value raises an exception"""

        kwarg = {}
        if record_func_reject_none in [
            builder.WaveformIn,
            builder.WaveformOut,
        ]:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

        with pytest.raises(self.expected_exceptions):
            record_func_reject_none("SOME-NAME", initial_value=None, **kwarg)

    def test_value_none_rejected_set_before_init(
        self, clear_records, record_func_reject_none
    ):
        """Test that setting \"None\" using .set() raises an exception"""

        kwarg = {}
        if record_func_reject_none in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

        with pytest.raises(self.expected_exceptions):
            record = record_func_reject_none("SOME-NAME", **kwarg)
            record.set(None)

    def none_value_test_func(self, record_func, queue):
        """Start the IOC and catch the expected exception"""

        log("CHILD: Child started")

        kwarg = {}
        if record_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": WAVEFORM_LENGTH}  # Must specify when no value

        record = record_func("SOME-NAME", **kwarg)

        log("CHILD: About to start IOC")

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        log("CHILD: Soft IOC started, about to .set(None)")

        try:
            record.set(None)
            log("CHILD: Uh-OH! No exception thrown when setting None!")
        except Exception as e:
            log("CHILD: Putting exception into queue %s", e)
            queue.put(e)
        else:
            log("CHILD: No exception raised when using None as value!")
            queue.put(Exception("FAIL: No exception raised during .set()"))

    @requires_cothread
    def test_value_none_rejected_set_after_init(self, record_func_reject_none):
        """Test that setting \"None\" using .set() after IOC init raises an
        exception"""
        ctx = get_multiprocessing_context()

        queue = ctx.Queue()

        process = ctx.Process(
            target=self.none_value_test_func,
            args=(record_func_reject_none, queue),
        )

        process.start()

        log("PARENT: Child process started, waiting for returned exception")

        try:
            exception = queue.get(timeout=TIMEOUT)

            assert isinstance(exception, self.expected_exceptions)
        finally:
            log("PARENT: Issuing terminate to child process")
            process.terminate()
            process.join(timeout=TIMEOUT)
            if process.exitcode is None:
                pytest.fail("Process did not terminate")


class TestInvalidValues:
    """Tests for values that records should reject"""

    def test_string_rejects_overlong_strings(self):
        """Test that stringIn & stringOut records reject strings >=39 chars"""

        OVERLONG_STR = MAX_LEN_STR + "A"

        with pytest.raises(ValueError):
            builder.stringIn("STRIN1", initial_value=OVERLONG_STR)

        with pytest.raises(ValueError):
            builder.stringOut("STROUT1", initial_value=OVERLONG_STR)

        with pytest.raises(ValueError):
            si = builder.stringIn("STRIN2")
            si.set(OVERLONG_STR)

        with pytest.raises(ValueError):
            so = builder.stringOut("STROUT2", initial_value=OVERLONG_STR)
            so.set(OVERLONG_STR)

    def test_long_string_rejects_overlong_strings(self):
        """Test that longStringIn & longStringOut records reject
        strings >=`WAVEFORM_LENGTH` chars"""
        OVERLONG_STR = MAX_LEN_STR + "A"

        with pytest.raises(AssertionError):
            builder.longStringIn(
                "LSTRIN1",
                initial_value=OVERLONG_STR,
                length=WAVEFORM_LENGTH)

        with pytest.raises(AssertionError):
            builder.longStringOut(
                "LSTROUT1",
                initial_value=OVERLONG_STR,
                length=WAVEFORM_LENGTH)

        with pytest.raises(AssertionError):
            lsi = builder.longStringIn("LSTRIN2", length=WAVEFORM_LENGTH)
            lsi.set(OVERLONG_STR)

        with pytest.raises(AssertionError):
            lso = builder.longStringIn("LSTROUT2", length=WAVEFORM_LENGTH)
            lso.set(OVERLONG_STR)

        # And a different way to initialise records to trigger same behaviour:
        with pytest.raises(AssertionError):
            lsi = builder.longStringIn("LSTRIN3", initial_value="ABC")
            lsi.set(OVERLONG_STR)

        with pytest.raises(AssertionError):
            lso = builder.longStringOut("LSTROUT3", initial_value="ABC")
            lso.set(OVERLONG_STR)


    def test_waveform_rejects_zero_length(self):
        """Test that WaveformIn/Out and longStringIn/Out records throw an
        exception when being initialized with a zero length array"""
        with pytest.raises(AssertionError):
            builder.WaveformIn("W_IN", [])
        with pytest.raises(AssertionError):
            builder.WaveformOut("W_OUT", [])
        with pytest.raises(AssertionError):
            builder.longStringIn("L_IN", length=0)
        with pytest.raises(AssertionError):
            builder.longStringOut("L_OUT", length=0)

    def test_waveform_rejects_overlong_values(self):
        """Test that Waveform records throw an exception when an overlong
        value is written"""
        w_in = builder.WaveformIn("W_IN", [1, 2, 3])
        w_out = builder.WaveformOut("W_OUT", [1, 2, 3])

        w_in_str = builder.WaveformIn("W_IN_STR", ["ABC", "DEF"])
        w_out_str = builder.WaveformOut("W_OUT_STR", ["ABC", "DEF"])

        with pytest.raises(AssertionError):
            w_in.set([1, 2, 3, 4])
        with pytest.raises(AssertionError):
            w_out.set([1, 2, 3, 4])
        with pytest.raises(AssertionError):
            w_in_str.set(["ABC", "DEF", "GHI"])
        with pytest.raises(AssertionError):
            w_out_str.set(["ABC", "DEF", "GHI"])

    def test_waveform_rejects_late_strings(self):
        """Test that a waveform won't allow a list of strings to be assigned
        if no string list was given in initial waveform construction"""
        w_in = builder.WaveformIn("W_IN", length=10)
        w_out = builder.WaveformOut("W_OUT", length=10)

        with pytest.raises(ValueError):
            w_in.set(["ABC", "DEF"])
        with pytest.raises(ValueError):
            w_out.set(["ABC", "DEF"])

    def test_waveform_rejects_long_array_of_strings(self):
        """Test that a waveform of strings won't accept too long strings"""
        w_in = builder.WaveformIn(
            "W_IN",
            initial_value=["123abc", "456def", "7890ghi"]
        )
        w_out = builder.WaveformIn(
            "W_OUT",
            initial_value=["123abc", "456def", "7890ghi"]
        )

        # Test putting too many elements
        with pytest.raises(AssertionError):
            w_in.set(["1", "2", "3", "4"])
        with pytest.raises(AssertionError):
            w_out.set(["1", "2", "3", "4"])

        # Test putting too long a string
        with pytest.raises(ValueError):
            w_in.set([VERY_LONG_STRING])
        with pytest.raises(ValueError):
            w_out.set([VERY_LONG_STRING])
