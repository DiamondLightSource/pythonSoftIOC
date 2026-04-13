"""Subprocess IOC for testing universal set() across SCAN settings.

Records created
---------------
AI          ai   Analog input, default SCAN='I/O Intr'.
AO          ao   Analog output, default SCAN='I/O Intr'.
LONGIN      longin  Long input, default SCAN='I/O Intr'.
BO          bo   Binary output, default SCAN='I/O Intr'.

The test harness sends commands over the multiprocessing connection:
  ("set", "AI", value)       -> calls record.set(value), replies "OK"
  ("get", "AI")              -> replies with record.get()
  ("scan", "AI", "Passive")  -> changes SCAN via dbpf, replies "OK"
  "D"                        -> shutdown
"""

import sys
from argparse import ArgumentParser
from multiprocessing.connection import Client

from softioc import softioc, builder, asyncio_dispatcher

from conftest import ADDRESS

if __name__ == "__main__":
    with Client(ADDRESS) as conn:
        parser = ArgumentParser()
        parser.add_argument(
            'prefix',
            help="The PV prefix for the records",
        )
        parsed_args = parser.parse_args()
        device_name = parsed_args.prefix
        builder.SetDeviceName(device_name)

        # ----- Records under test -----
        t_ai = builder.aIn(
            "AI",
            initial_value=0.0,
            PREC=3,
        )

        t_ao = builder.aOut(
            "AO",
            initial_value=0.0,
            always_update=True,
            PREC=3,
        )

        t_longin = builder.longIn(
            "LONGIN",
            initial_value=0,
        )

        t_bo = builder.boolOut(
            "BO",
            initial_value=False,
            always_update=True,
        )

        records = {
            "AI": t_ai,
            "AO": t_ao,
            "LONGIN": t_longin,
            "BO": t_bo,
        }

        # ----- Boot the IOC -----
        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher)

        conn.send("R")  # "Ready"

        # ----- Command loop -----
        while True:
            msg = conn.recv()
            if msg == "D":
                break
            elif isinstance(msg, tuple):
                cmd = msg[0]
                if cmd == "set":
                    _, rec_name, value = msg
                    records[rec_name].set(value)
                    conn.send("OK")
                elif cmd == "get":
                    _, rec_name = msg
                    conn.send(records[rec_name].get())
                elif cmd == "scan":
                    # Change SCAN via softioc.dbpf to bypass DISP
                    _, rec_name, scan_value = msg
                    pv_name = f"{device_name}:{rec_name}.SCAN"
                    softioc.dbpf(pv_name, scan_value)
                    conn.send("OK")
                else:
                    conn.send("ERR")
            else:
                conn.send("ERR")

        sys.stdout.flush()
        sys.stderr.flush()
