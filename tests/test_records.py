import multiprocessing
import numpy
import os
import pytest

from softioc import builder, softioc
from epicsdbbuilder import ResetRecords
from softioc.device_core import RecordLookup
import sim_records

# Counter for unique record number
counter = 0

@pytest.fixture
def record_number():
    """Unique counter for record naming"""
    global counter
    counter += 1
    return counter


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

def idfn(fixture_value):
    """Provide a nice name for the tests in the results list"""
    return fixture_value[0].__name__ + "-" + fixture_value[3].__name__

# TODO:
# - unicode chars in strings
# - bytestrings
# - too long strings, exactly 40 char strings, empty strings.
@pytest.fixture(params=[
        (builder.aOut, 5.5, 5.5, float),
        (builder.aIn, 5.5, 5.5, float),
        (builder.longOut, 5, 5, int),
        (builder.longIn, 5, 5, int),
        (builder.boolOut, 1, 1, int),
        (builder.boolIn, 1, 1, int),
        (builder.stringOut, "abc", "abc", str),
        (builder.stringIn, "abc", "abc", str),
        (builder.mbbIn, 1, 1, int),
        (builder.mbbOut, 1, 1, int),
        (builder.WaveformIn, [1, 2, 3], [1, 2, 3], list),
        (builder.WaveformOut, [1, 2, 3], [1, 2, 3], list),
        (
            builder.WaveformIn,
            "ABC",
            numpy.array([65, 66, 67, 0], dtype=numpy.uint8),
            numpy.array
        )
    ],
    ids=idfn)
def record_values(request):
    """A collection of record creation functions, an initial value, an expected
    returned value, and the expected type of the returned value"""
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
            f"Arrays not equal: {actual_value} {expected_value}"
    else:
        assert actual_value == expected_value
        assert type(actual_value) == expected_type

def test_value_retrieval_pre_init_set(
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


def run_test_function(creation_func, expected_value, expected_type, test_func):
    """Helper function to handle the multiprocessing process"""
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=test_func, args=(queue,))
    process.start()

    try:
        rec_val = queue.get(timeout=5)

        record_value_asserts(
            creation_func,
            rec_val,
            expected_value,
            expected_type)
    finally:
        process.join()

def test_value_retrieval_pre_init_initial_value(
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

def test_value_retrieval_post_init_set(record_values):
    """Test that records provide the expected values on get calls when using
    .set() before IOC initialisation and .get() after initialisation"""

    creation_func, initial_value, expected_value, expected_type = record_values

    def inner_func(queue):
        kwarg = {}
        if creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        out_rec = creation_func("out-record", **kwarg)
        out_rec.set(initial_value)

        builder.LoadDatabase()
        softioc.iocInit()

        queue.put(out_rec.get())

    run_test_function(creation_func, expected_value, expected_type, inner_func)

def test_value_retrieval_post_init_initial_value(record_values):
    """Test that records provide the expected values on get calls when using
    initial_value during record creation and .get() after IOC initialisation"""

    creation_func, initial_value, expected_value, expected_type = record_values

    def inner_func(queue):
        out_rec = creation_func("out-record", initial_value=initial_value)

        builder.LoadDatabase()
        softioc.iocInit()

        queue.put(out_rec.get())

    run_test_function(creation_func, expected_value, expected_type, inner_func)

def test_value_retrieval_post_init_set_after_init(record_values):
    """Test that records provide the expected values on get calls when using
    .set() and .get() after IOC initialisation"""

    creation_func, initial_value, expected_value, expected_type = record_values

    def inner_func(queue):
        kwarg = {}
        if creation_func in [builder.WaveformIn, builder.WaveformOut]:
            kwarg = {"length": 50}  # Required when no value on creation

        out_rec = creation_func("out-record", **kwarg)

        builder.LoadDatabase()
        softioc.iocInit()
        out_rec.set(initial_value)

        queue.put(out_rec.get())

    run_test_function(creation_func, expected_value, expected_type, inner_func)
