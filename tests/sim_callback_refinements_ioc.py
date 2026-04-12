"""Subprocess IOC for testing callback refinements.

Tests:
- Multi-field on_field_change (list form)
- on_update coexistence with field callbacks
- auto_reset_scan behavior (when enabled via iocInit flag)

Records
-------
AO          ao   Main record with on_update and field callbacks.
ON-UPDATE-CNT   Incremented by on_update.
MULTI-CB-CNT    Incremented by multi-field callback (DRVH, DRVL, HIHI).
WILDCARD-CNT    Incremented by * wildcard callback.
VAL-CB-CNT      Incremented by VAL field callback.
SCAN-CB-CNT     Incremented by SCAN field callback.
LAST-SCAN-VAL   Stores the last SCAN value seen by the callback.
"""

import sys
from argparse import ArgumentParser
from multiprocessing.connection import Client

from softioc import softioc, builder, asyncio_dispatcher

from conftest import ADDRESS, select_and_recv

if __name__ == "__main__":
    with Client(ADDRESS) as conn:
        parser = ArgumentParser()
        parser.add_argument('prefix')
        parser.add_argument(
            '--auto-reset-scan', action='store_true', default=False)
        parsed_args = parser.parse_args()
        builder.SetDeviceName(parsed_args.prefix)

        # ----- Counter PVs -----
        on_update_cnt = builder.longOut(
            "ON-UPDATE-CNT", initial_value=0)
        multi_cb_cnt = builder.longOut(
            "MULTI-CB-CNT", initial_value=0)
        wildcard_cnt = builder.longOut(
            "WILDCARD-CNT", initial_value=0)
        val_cb_cnt = builder.longOut(
            "VAL-CB-CNT", initial_value=0)
        scan_cb_cnt = builder.longOut(
            "SCAN-CB-CNT", initial_value=0)
        last_scan_val = builder.stringOut(
            "LAST-SCAN-VAL", initial_value="")
        dereg_cnt = builder.longOut(
            "DEREG-CB-CNT", initial_value=0)

        # ----- Main record under test -----
        def ao_on_update(value):
            on_update_cnt.set(on_update_cnt.get() + 1)

        t_ao = builder.aOut(
            "AO",
            initial_value=0.0,
            on_update=ao_on_update,
            always_update=True,
            DRVL=-50.0,
            DRVH=50.0,
            HIHI=90.0,
            PREC=3,
        )

        # ----- Boot the IOC -----
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(
            dispatcher,
            log_puts=False,
            auto_reset_scan=parsed_args.auto_reset_scan,
        )

        # ---- Register callbacks (CLS) -----

        # Multi-field subscription: single callback for DRVH, DRVL, HIHI
        def _multi_cb(rec_name, field, value):
            multi_cb_cnt.set(multi_cb_cnt.get() + 1)
        t_ao.on_field_change(["DRVH", "DRVL", "HIHI"], _multi_cb)

        # Wildcard
        def _wildcard_cb(rec_name, field, value):
            wildcard_cnt.set(wildcard_cnt.get() + 1)
        t_ao.on_field_change("*", _wildcard_cb)

        # VAL-specific
        def _val_cb(rec_name, field, value):
            val_cb_cnt.set(val_cb_cnt.get() + 1)
        t_ao.on_field_change("VAL", _val_cb)

        # SCAN-specific: also stores the value
        def _scan_cb(rec_name, field, value):
            scan_cb_cnt.set(scan_cb_cnt.get() + 1)
            last_scan_val.set(value[:39])
        t_ao.on_field_change("SCAN", _scan_cb)

        # --- De-registration support ---
        # A second DRVH callback that can be removed on command.
        def _dereg_cb(rec_name, field, value):
            dereg_cnt.set(dereg_cnt.get() + 1)
        t_ao.on_field_change("DRVH", _dereg_cb)

        conn.send("R")  # "Ready"

        # Protocol: test sends "P" (phase-2: deregister) or "D" (done).
        msg = select_and_recv(conn)
        if msg == "P":
            t_ao.remove_field_callback("DRVH", _dereg_cb)
            conn.send("K")  # acknowledged
            select_and_recv(conn, "D")
        else:
            assert msg == "D"

        sys.stdout.flush()
        sys.stderr.flush()

        conn.send("D")  # "Done" acknowledgement
