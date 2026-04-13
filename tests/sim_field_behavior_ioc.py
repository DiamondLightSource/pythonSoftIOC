"""Subprocess IOC for testing how PV field writes interact with
pythonSoftIOC's device-support layer and the underlying EPICS
record processing.

Records created
---------------
AO          ao   Main analog-output record with alarm limits, drive
                 limits, initial SCAN='I/O Intr', on_update callback.
AI          ai   Analog-input that mirrors the AO value via on_update.
BO          bo   Binary-output with on_update.
LONGIN      longin  Long-input, updated by Python only.

Counter PVs (longOut) — incremented by the corresponding callback
so the test can verify that the callback fired.

AO-UPDATE-CNT   Incremented every time on_update fires for AO.
AO-PROCESS-CNT  Incremented every time AO's _process runs
                 (raw device-support level).
AI-VAL          Holds the AI value after set().
BO-UPDATE-CNT   Incremented every time on_update fires for BO.

The IOC also records the last field-change notification it sees
(CLS extension) for AO:
LAST-FIELD      stringOut holding the last field name.
LAST-VALUE      stringOut holding the last value string.
"""

import sys
from argparse import ArgumentParser
from multiprocessing.connection import Client

from softioc import (
    softioc, builder,
    asyncio_dispatcher, pvlog,
)

from conftest import ADDRESS, select_and_recv

if __name__ == "__main__":
    with Client(ADDRESS) as conn:
        parser = ArgumentParser()
        parser.add_argument(
            'prefix',
            help="The PV prefix for the records",
        )
        parsed_args = parser.parse_args()
        builder.SetDeviceName(parsed_args.prefix)

        # ----- Counter / mirror PVs -----
        ao_update_cnt = builder.longOut(
            "AO-UPDATE-CNT", initial_value=0,
        )
        ao_process_cnt = builder.longOut(
            "AO-PROCESS-CNT", initial_value=0,
        )
        ai_val = builder.aOut(
            "AI-VAL", initial_value=0.0,
        )
        bo_update_cnt = builder.longOut(
            "BO-UPDATE-CNT", initial_value=0,
        )
        last_field = builder.stringOut(
            "LAST-FIELD", initial_value="",
        )
        last_value = builder.stringOut(
            "LAST-VALUE", initial_value="",
        )

        # ----- Primary records under test -----
        def ao_on_update(value):
            ao_update_cnt.set(ao_update_cnt.get() + 1)

        t_ao = builder.aOut(
            "AO",
            initial_value=0.0,
            on_update=ao_on_update,
            always_update=True,
            LOPR=-100.0,
            HOPR=100.0,
            DRVL=-50.0,
            DRVH=50.0,
            HIHI=90.0,
            HIGH=70.0,
            LOW=-70.0,
            LOLO=-90.0,
            HHSV="MAJOR",
            HSV="MINOR",
            LSV="MINOR",
            LLSV="MAJOR",
            PREC=3,
            EGU="V",
        )

        t_ai = builder.aIn(
            "AI",
            initial_value=0.0,
            LOPR=-100.0,
            HOPR=100.0,
            HIHI=90.0,
            HIGH=70.0,
            LOW=-70.0,
            LOLO=-90.0,
            HHSV="MAJOR",
            HSV="MINOR",
            LSV="MINOR",
            LLSV="MAJOR",
            PREC=3,
            EGU="V",
        )

        def bo_on_update(value):
            bo_update_cnt.set(bo_update_cnt.get() + 1)

        t_bo = builder.boolOut(
            "BO",
            initial_value=False,
            on_update=bo_on_update,
            always_update=True,
        )

        t_longin = builder.longIn(
            "LONGIN",
            initial_value=0,
        )

        # ----- Boot the IOC -----
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        # ----- Register field-change callbacks (CLS) -----
        def _on_any_field(rec_name, field, value):
            last_field.set(field)
            last_value.set(value)

        t_ao.on_field_change("*", _on_any_field)

        conn.send("R")  # "Ready"

        select_and_recv(conn, "D")  # "Done"

        sys.stdout.flush()
        sys.stderr.flush()
