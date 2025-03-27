import asyncio
from contextlib import nullcontext

import pytest

from conftest import (
    aioca_cleanup,
    log,
    create_random_prefix,
    TIMEOUT,
    select_and_recv,
    get_multiprocessing_context,
)

from softioc import asyncio_dispatcher, builder, softioc


class TestPVAccess:
    """Tests related to PVAccess"""

    record_name = "PVA_AOut"
    record_value = 10

    def pva_test_func(self, device_name, conn, use_pva):
        builder.SetDeviceName(device_name)

        builder.aOut(self.record_name, initial_value=self.record_value)

        dispatcher = asyncio_dispatcher.AsyncioDispatcher()
        builder.LoadDatabase()
        softioc.iocInit(dispatcher=dispatcher, enable_pva=use_pva)

        conn.send("R")  # "Ready"
        log("CHILD: Sent R over Connection to Parent")

        # Keep process alive while main thread works.
        while (True):
            if conn.poll(TIMEOUT):
                val = conn.recv()
                if val == "D":  # "Done"
                    break

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "use_pva,expectation",
        [
            (True, nullcontext()),
            (False, pytest.raises(asyncio.TimeoutError))
        ]
    )
    async def test_pva_enable_disable(self, use_pva, expectation):
        """Test that we can enable and disable PVA, perform PVAccess requests
        when enabled, and that we can always do Channel Access requests"""
        ctx = get_multiprocessing_context()
        parent_conn, child_conn = ctx.Pipe()

        device_name = create_random_prefix()

        process = ctx.Process(
            target=self.pva_test_func,
            args=(device_name, child_conn, use_pva),
        )

        process.start()

        from aioca import caget
        from p4p.client.asyncio import Context
        try:
            # Wait for message that IOC has started
            select_and_recv(parent_conn, "R")

            record_full_name = device_name + ":" + self.record_name

            ret_val = await caget(record_full_name, timeout=TIMEOUT)

            assert ret_val == self.record_value

            with expectation as _:
                with Context("pva") as ctx:
                    # Short timeout as, if the above CA connection has happened
                    # there's no need to wait a very long time for the PVA
                    # connection
                    pva_val = await asyncio.wait_for(
                        ctx.get(record_full_name),
                        timeout=2
                    )
                    assert pva_val == self.record_value


        finally:
            # Clear the cache before stopping the IOC stops
            # "channel disconnected" error messages
            aioca_cleanup()
            parent_conn.send("D")  # "Done"
            process.join(timeout=TIMEOUT)
