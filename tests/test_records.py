import os
import pytest

from softioc import builder

import sim_records


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
