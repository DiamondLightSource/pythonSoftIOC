from importlib import reload
import random
import string
import os
import sys

from softioc import softioc, builder
from cothread.catools import caget, caput

import sim_records

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12))


def test_records(tmp_path):
    path = tmp_path / "records.db"
    builder.WriteRecords(path)
    expected = os.path.join(os.path.dirname(__file__), "expected_records.db")
    assert open(path).readlines()[4:] == open(expected).readlines()[4:]


def assert_record_equals(record, value):
    assert record.get() == caget(record.name) == value

def test_ioc(capsys):
    builder.ResetRecords()
    builder.SetDeviceName(PV_PREFIX)
    reload(sim_records)
    builder.LoadDatabase()
    softioc.iocInit()
    out, err = capsys.readouterr()
    assert not out
    assert not err
    assert caget(PV_PREFIX + ":UPTIME") in ["00:00:00", "00:00:01"]
    # AI
    assert_record_equals(sim_records.t_ai, 12.34)
    sim_records.t_ai.set(34)
    assert_record_equals(sim_records.t_ai, 34)
    # STRINGOUT
    assert_record_equals(sim_records.t_stringout, "watevah")
    caput(PV_PREFIX + ":STRINGOUT", "something", wait=True)
    out, err = capsys.readouterr()
    assert out == "on_update 'something'\n"
    assert not err
    assert_record_equals(sim_records.t_stringout, "something")
    sim_records.t_stringout.set(b"something else")
    assert_record_equals(sim_records.t_stringout, "something else")





if __name__ == "__main__":
    softioc.interactive_ioc(globals())
