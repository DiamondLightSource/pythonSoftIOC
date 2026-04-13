"""Simulated IOC for CLS field-change callback tests.

Creates a small set of records and registers ``on_field_change`` callbacks via
the CLS extension.  Counter PVs are incremented each time a callback fires,
allowing the test client to verify behaviour over CA or PVA.

Records created
---------------
``{prefix}:AO``
    The record whose fields the test client writes to.
``{prefix}:SCAN-CB-CNT``
    Incremented by the SCAN callback.
``{prefix}:DISA-CB-CNT``
    Incremented by the DISA callback.
``{prefix}:VAL-CB-CNT``
    Incremented by the VAL callback.
``{prefix}:HIHI-CB-CNT``
    Incremented by the HIHI callback (alarm field, DBF_DOUBLE).
``{prefix}:DESC-CB-CNT``
    Incremented by the DESC callback (string field, DBF_STRING).
``{prefix}:ANY-CB-CNT``
    Incremented by a wildcard ``"*"`` callback (fires on **every** field
    write).

Expected behaviour
------------------
- Original (upstream) pythonSoftIOC: ``on_field_change`` does not exist, so
  this script raises ``AttributeError`` before printing READY.
- CLS fork: all callbacks register successfully and READY is printed.
"""

import sys
from argparse import ArgumentParser
from multiprocessing.connection import Client

from softioc import softioc, builder, asyncio_dispatcher

from conftest import ADDRESS, select_and_recv


if __name__ == "__main__":
    with Client(ADDRESS) as conn:
        parser = ArgumentParser()
        parser.add_argument("prefix", help="PV prefix for the records")
        parsed_args = parser.parse_args()
        builder.SetDeviceName(parsed_args.prefix)

        # Main record whose fields the test client writes to.
        ao = builder.aOut("AO", initial_value=0.0, HIHI=90.0, HIGH=70.0)

        # Counter PVs — incremented by the corresponding callback.
        scan_cnt = builder.longOut("SCAN-CB-CNT", initial_value=0)
        disa_cnt = builder.longOut("DISA-CB-CNT", initial_value=0)
        val_cnt = builder.longOut("VAL-CB-CNT", initial_value=0)
        hihi_cnt = builder.longOut("HIHI-CB-CNT", initial_value=0)
        desc_cnt = builder.longOut("DESC-CB-CNT", initial_value=0)
        any_cnt = builder.longOut("ANY-CB-CNT", initial_value=0)

        # Boot the IOC.
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        # ---- Register on_field_change callbacks (CLS extension) ----------
        # With upstream pythonSoftIOC this raises AttributeError.

        def _make_increment(counter):
            """Return a callback that increments *counter* by one."""
            def _cb(rec_name, field, value):
                counter.set(counter.get() + 1)
            return _cb

        # Per-field callbacks.
        ao.on_field_change("SCAN", _make_increment(scan_cnt))
        ao.on_field_change("DISA", _make_increment(disa_cnt))
        ao.on_field_change("VAL",  _make_increment(val_cnt))
        # DBF_DOUBLE alarm field
        ao.on_field_change("HIHI", _make_increment(hihi_cnt))
        # DBF_STRING metadata field
        ao.on_field_change("DESC", _make_increment(desc_cnt))

        # Wildcard callback — fires for every field write on this record.
        ao.on_field_change("*", _make_increment(any_cnt))

        conn.send("R")  # "Ready"

        # Keep the process alive until the test tells us to stop.
        select_and_recv(conn, "D")  # "Done"

        sys.stdout.flush()
        sys.stderr.flush()

        conn.send("D")  # "Done" acknowledgement
