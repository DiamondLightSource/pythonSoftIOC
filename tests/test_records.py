import os
import pytest

from softioc import builder

import sim_records
import numpy

def test_records(tmp_path):
    path = str(tmp_path / "records.db")
    builder.WriteRecords(path)
    expected = os.path.join(os.path.dirname(__file__), "expected_records.db")
    assert open(path).readlines()[5:] == open(expected).readlines()

def test_enum_length_restriction():
    """Test that supplying too many labels (more than maximum of 16) raises expected
    exception"""
    with pytest.raises(AssertionError):
        builder.mbbIn(
                "ManyLabels", "one", "two", "three", "four", "five", "six",
                "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
                "fourteen", "fifteen", "sixteen", "seventeen")


def test__waveform_fields_nelm_used():
    """Test that the waveform construction returns the expected fields - i.e. NELM
    is the same as the input value. Test for issue #37"""
    fields = {"initial_value": numpy.array([1, 2, 3]), "NELM": 999}
    builder._waveform(None, fields)
    assert fields["NELM"] == 999
