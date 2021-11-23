# -*- coding: utf-8 -*-
import ctypes
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
    """Provide a nice name for the tests in the record_values fixture"""
    return fixture_value[0].__name__ + "-" + type(fixture_value[1]).__name__ \
        + "-" + fixture_value[3].__name__

@pytest.fixture(params=[
        (builder.aOut, 5.5, 5.5, float),
        (builder.aIn, 5.5, 5.5, float),
        (builder.aOut, 3, 3., float),
        (builder.aIn, 3, 3., float),
        (builder.aOut, ctypes.c_float(3.5), 3.5, float),
        (builder.aIn, ctypes.c_float(3.5), 3.5, float),
        (builder.longOut, 5, 5, int),
        (builder.longIn, 5, 5, int),
        (builder.longOut, 9.9, 9, int),
        (builder.longIn, 9.9, 9, int),
        (builder.longOut, ctypes.c_int(6), 6, int),
        (builder.longIn, ctypes.c_int(6), 6, int),
        (builder.boolOut, 1, 1, int),
        (builder.boolIn, 1, 1, int),
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
    ids=idfn)
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
        # Python2 handles UTF-8 differently so needs extra encoding
        if sys.version_info == (2, 7) and expected_type == str:
            expected_value = expected_value.encode('utf-8')

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

def test_value_post_init_set(record_values):
    """Test that records provide the expected values on get calls when using
    .set() before IOC initialisation and .get() after initialisation"""

    run_test_function(record_values, SetValueEnum.SET_BEFORE_INIT)

def test_value_post_init_initial_value(record_values):
    """Test that records provide the expected values on get calls when using
    initial_value during record creation and .get() after IOC initialisation"""

    run_test_function(record_values, SetValueEnum.INITIAL_VALUE)

def test_value_post_init_set_after_init(record_values):
    """Test that records provide the expected values on get calls when using
    .set() and .get() after IOC initialisation"""

    run_test_function(record_values, SetValueEnum.SET_AFTER_INIT)
