import multiprocessing
import numpy
import os
import pytest
import sys

from enum import Enum

from softioc import builder, softioc
from epicsdbbuilder import ResetRecords
from softioc.device_core import RecordLookup
import sim_records

requires_cothread = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Cothread doesn't work on windows"
)


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

def record_funcs_names(fixture_value):
    """Provide a nice name for the record_funcs fixture"""
    return fixture_value.__name__


@pytest.fixture(params=[
        builder.aIn,
        builder.aOut,
        builder.longIn,
        builder.longOut,
        builder.boolIn,
        builder.boolOut,
        builder.stringIn,
        builder.stringOut,
        builder.mbbIn,
        builder.mbbOut,
        builder.WaveformIn,
        builder.WaveformOut,
    ],
    ids=record_funcs_names)
def record_funcs(request):
    """The list of record creation functions"""
    return request.param


def record_values_names(fixture_value):
    """Provide a nice name for the tests in the record_values fixture"""
    return fixture_value[0].__name__ + "-" + type(fixture_value[1]).__name__ \
        + "-" + fixture_value[3].__name__

@pytest.fixture(params=[
        (builder.aOut, 5.5, 5.5, float),
        (builder.aIn, 5.5, 5.5, float),
        (builder.aOut, 3, 3., float),
        (builder.aIn, 3, 3., float),
        (builder.longOut, 5, 5, int),
        (builder.longIn, 5, 5, int),
        (builder.longOut, 9.9, 9, int),
        (builder.longIn, 9.9, 9, int),
        (builder.boolOut, 1, 1, int),
        (builder.boolIn, 1, 1, int),
        (builder.boolOut, True, 1, int),
        (builder.boolIn, True, 1, int),
        (builder.boolOut, False, 0, int),
        (builder.boolIn, False, 0, int),
        (builder.stringOut, "abc", "abc", str),
        (builder.stringIn, "abc", "abc", str),
        (builder.stringOut, "", "", str),
        (builder.stringIn, "", "", str),
        (builder.stringOut, b"abc", "abc", str),
        (builder.stringIn, b"abc", "abc", str),
        (builder.stringOut, b"a\xcfb", "a�b", str),  # Invalid UTF-8
        (builder.stringIn, b"a\xcfb", "a�b", str),  # Invalid UTF-8
        (builder.stringOut, b"a\xe2\x82\xacb", "a€b", str),  # Valid UTF-8
        (builder.stringIn, b"a\xe2\x82\xacb", "a€b", str),  # Valid UTF-8
        (builder.stringOut, "a€b", "a€b", str),  # Valid UTF-8
        (builder.stringIn, "a€b", "a€b", str),  # Valid UTF-8
        (
            builder.stringOut,
            "this string is much longer than 40 characters",
            "this string is much longer than 40 char",
            str
        ),
        (
            builder.stringIn,
            "this string is much longer than 40 characters",
            "this string is much longer than 40 char",
            str
        ),
        (builder.mbbIn, 1, 1, int),
        (builder.mbbOut, 1, 1, int),
        (
            builder.WaveformIn,
            [1, 2, 3],
            numpy.array([1, 2, 3], dtype=numpy.float32),
            numpy.ndarray
        ),
        (
            builder.WaveformOut,
            [1, 2, 3],
            numpy.array([1, 2, 3], dtype=numpy.float32),
            numpy.ndarray
        ),
        (
            builder.WaveformIn,
            "ABC",
            numpy.array([65, 66, 67, 0], dtype=numpy.uint8),
            numpy.ndarray
        ),
        (
            builder.WaveformOut,
            "ABC",
            numpy.array([65, 66, 67, 0], dtype=numpy.uint8),
            numpy.ndarray
        ),
        (
            builder.WaveformIn,
            b"HELLO\0WORLD",
            numpy.array([72, 69, 76, 76, 79,  0, 87, 79, 82, 76, 68, 0],
                        dtype=numpy.uint8),
            numpy.ndarray
        ),
        (
            builder.WaveformOut,
            b"HELLO\0WORLD",
            numpy.array([72, 69, 76, 76, 79,  0, 87, 79, 82, 76, 68, 0],
                        dtype=numpy.uint8),
            numpy.ndarray
        )
    ],
    ids=record_values_names)
def record_values(request):
    """A list of parameters for record value setting/getting tests.

    Fields are:
    - Record builder function
    - Input value passed to .set() or used in initial_value on record creation
    - Expected output value after doing .get()
    - Expected type of the output value from .get()"""
    return request.param  # One item from the params list

def test_records(tmp_path):
    path = str(tmp_path / "records.db")
    builder.WriteRecords(path)
    expected = os.path.join(os.path.dirname(__file__), "expected_records.db")
    assert open(path).readlines()[5:] == open(expected).readlines()

def test_enum_length_restriction():
    with pytest.raises(AssertionError):
        builder.mbbIn(
                "ManyLabels", "one", "two", "three", "four", "five", "six",
                "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
                "fourteen", "fifteen", "sixteen", "seventeen")

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
        creation_func,
        actual_value,
        expected_value,
        expected_type):
    """Asserts that the expected value and expected type are matched with
    the actual value. Handles both scalar and waveform data"""

    if creation_func in [builder.WaveformOut, builder.WaveformIn]:
        assert numpy.array_equal(actual_value, expected_value), \
            "Arrays not equal: {} {}".format(actual_value, expected_value)
        assert type(actual_value) == expected_type
    else:
        assert actual_value == expected_value
        assert type(actual_value) == expected_type

def test_value_pre_init_set(
        clear_records,
        record_values):
    """Test that records provide the expected values on get calls when using
    .set() and .get() before IOC initialisation occurs"""

    creation_func, initial_value, expected_value, expected_type = record_values

    kwarg = {}
    if creation_func in [builder.WaveformIn, builder.WaveformOut]:
        kwarg = {"length": 50}  # Required when no value on creation

    out_rec = creation_func("out-record", **kwarg)
    out_rec.set(initial_value)

    record_value_asserts(
        creation_func,
        out_rec.get(),
        expected_value,
        expected_type)


def test_value_pre_init_initial_value(
        clear_records,
        record_values):
    """Test that records provide the expected values on get calls when using
    initial_value and .get() before IOC initialisation occurs"""

    creation_func, initial_value, expected_value, expected_type = record_values

    out_rec = creation_func("out-record", initial_value=initial_value)

    record_value_asserts(
        creation_func,
        out_rec.get(),
        expected_value,
        expected_type)

class SetValueEnum(Enum):
    """Enum to control when and how the record's value should be set"""
    INITIAL_VALUE = 1
    SET_BEFORE_INIT = 2
    SET_AFTER_INIT = 3
    NO_VALUE = 4

def value_test_function(creation_func, initial_value, queue, set_enum):
    kwarg = {}

    if set_enum == SetValueEnum.INITIAL_VALUE:
        kwarg.update({"initial_value": initial_value})
    elif creation_func in [builder.WaveformIn, builder.WaveformOut]:
        kwarg = {"length": 50}  # Required when no value on creation
        # Related to this issue:
        # https://github.com/dls-controls/pythonSoftIOC/issues/37


    out_rec = creation_func("out-record", **kwarg)

    if set_enum == SetValueEnum.SET_BEFORE_INIT:
        out_rec.set(initial_value)

    builder.LoadDatabase()
    softioc.iocInit()

    if set_enum == SetValueEnum.SET_AFTER_INIT:
        out_rec.set(initial_value)

    queue.put(out_rec.get())


def run_test_function(record_values, set_enum):
    """Run the test function using multiprocessing and check returned value is
    expected value"""

    creation_func, initial_value, expected_value, expected_type = record_values

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=value_test_function,
        args=(creation_func, initial_value, queue, set_enum)
    )

    process.start()

    try:
        rec_val = queue.get(timeout=5)

        record_value_asserts(
            creation_func,
            rec_val,
            expected_value,
            expected_type)
    finally:
        process.terminate()
        process.join(timeout=3)

@requires_cothread
def test_value_post_init_set(record_values):
    """Test that records provide the expected values on get calls when using
    .set() before IOC initialisation and .get() after initialisation"""

    run_test_function(record_values, SetValueEnum.SET_BEFORE_INIT)

@requires_cothread
def test_value_post_init_initial_value(record_values):
    """Test that records provide the expected values on get calls when using
    initial_value during record creation and .get() after IOC initialisation"""

    run_test_function(record_values, SetValueEnum.INITIAL_VALUE)

@requires_cothread
def test_value_post_init_set_after_init(record_values):
    """Test that records provide the expected values on get calls when using
    .set() and .get() after IOC initialisation"""

    run_test_function(record_values, SetValueEnum.SET_AFTER_INIT)

@pytest.mark.parametrize("creation_func,expected_value,expected_type", [
    (builder.aOut, None, type(None)),
    (builder.aIn, 0.0, float),
    (builder.longOut, None, type(None)),
    (builder.longIn, 0, int),
    (builder.boolOut, None, type(None)),
    (builder.boolIn, 0, int),
    (builder.stringOut, None, type(None)),
    (builder.stringIn, "", str),
    (builder.mbbOut, None, type(None)),
    (builder.mbbIn, 0, int),
    (builder.WaveformOut, None, type(None)),
    (builder.WaveformIn, [], numpy.ndarray),
])
def test_value_default_pre_init(
        creation_func,
        expected_value,
        expected_type,
        clear_records):
    """Test that the correct default values are returned from .get() (before
    record initialisation) when no initial_value or .set() is done"""

    kwarg = {}
    if creation_func in [builder.WaveformIn, builder.WaveformOut]:
        kwarg = {"length": 50}  # Required when no value on creation

    out_rec = creation_func("out-record", **kwarg)
    record_value_asserts(
        creation_func,
        out_rec.get(),
        expected_value,
        expected_type)


@requires_cothread
@pytest.mark.parametrize("creation_func,expected_value,expected_type", [
    (builder.aOut, 0.0, float),
    (builder.aIn, 0.0, float),
    (builder.longOut, 0, int),
    (builder.longIn, 0, int),
    (builder.boolOut, 0, int),
    (builder.boolIn, 0, int),
    (builder.stringOut, "", str),
    (builder.stringIn, "", str),
    (builder.mbbOut, 0, int),
    (builder.mbbIn, 0, int),
    (builder.WaveformOut, [], numpy.ndarray),
    (builder.WaveformIn, [], numpy.ndarray),
])
def test_value_default_post_init(creation_func, expected_value, expected_type):
    """Test that records provide the expected default value after they are
    initialised, having never had a value set"""

    # Add a dummy initial_value to the tuple, so we can use the same framework
    # as the other tests
    tmp = list((creation_func, expected_value, expected_type))
    tmp.insert(1, None)
    run_test_function(tuple(tmp), SetValueEnum.NO_VALUE)


def test_value_none_rejected_initial_value(clear_records, record_funcs):
    """Test that setting \"None\" as the initial_value raises an exception"""

    kwarg = {}
    if record_funcs in [builder.WaveformIn, builder.WaveformOut]:
        kwarg = {"length": 50}  # Required when no value on creation

    with pytest.raises((ValueError, TypeError)):
        record_funcs("SOME-NAME", initial_value=None, **kwarg)

def test_value_none_rejected_set_before_init(clear_records, record_funcs):
    """Test that setting \"None\" using .set() raises an exception"""

    kwarg = {}
    if record_funcs in [builder.WaveformIn, builder.WaveformOut]:
        kwarg = {"length": 50}  # Required when no value on creation

    with pytest.raises((ValueError, TypeError)):
        record = record_funcs("SOME-NAME", **kwarg)
        record.set(None)

@requires_cothread
def test_value_none_rejected_set_after_init(record_funcs):
    """Test that setting \"None\" using .set() after IOc init raises an
    exception"""

    def inner_func(record_func, queue):
        """Start the IOC and catch the expected exception"""
        kwarg = {}
        if record_funcs in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        record = record_funcs("SOME-NAME", **kwarg)

        builder.LoadDatabase()
        softioc.iocInit()

        try:
            record.set(None)
        except Exception as e:
            queue.put(e)

        queue.put(Exception("FAIL:Test did not raise exception during .set()"))


    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=inner_func,
        args=(record_funcs, queue)
    )

    process.start()

    try:
        exception = queue.get(timeout=5)

        assert isinstance(exception, (ValueError, TypeError))
    finally:
        process.terminate()
        process.join(timeout=3)
