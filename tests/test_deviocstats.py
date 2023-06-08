# File for tests related to devIocStats support module, which at time of writing
# is built alongside PythonSoftIOC and optionally turned on at runtime

import multiprocessing
import pytest

from conftest import (
    create_random_prefix,
    TIMEOUT,
    select_and_recv,
    get_multiprocessing_context
)

from softioc import asyncio_dispatcher, builder, softioc

def deviocstats_test_func(
        device_name,
        child_conn):
    """Start the IOC with the specified validate method"""

    builder.SetDeviceName(device_name)

    dispatcher = asyncio_dispatcher.AsyncioDispatcher()
    builder.LoadDatabase()
    softioc.devIocStats(device_name)
    softioc.iocInit(dispatcher)

    child_conn.send("R")

    # Keep process alive while main thread runs CAGET
    if child_conn.poll(TIMEOUT):
        val = child_conn.recv()
        assert val == "D", "Did not receive expected Done character"

@pytest.mark.asyncio
async def test_deviocstats():

    ctx = get_multiprocessing_context()

    parent_conn, child_conn = ctx.Pipe()

    device_name = create_random_prefix()

    process = ctx.Process(
        target=deviocstats_test_func,
        args=(device_name, child_conn),
    )

    process.start()

    from aioca import caget, purge_channel_caches

    try:
        # Wait for message that IOC has started
        select_and_recv(parent_conn, "R")

        # Suppress potential spurious warnings
        purge_channel_caches()

        cpu_cnt = await caget(device_name + ":CPU_CNT")
        assert cpu_cnt == multiprocessing.cpu_count()

        ioc_cpu_load = await caget(device_name + ":IOC_CPU_LOAD")
        assert ioc_cpu_load == pytest.approx(0, abs=1e-2)


    finally:
        # Suppress potential spurious warnings
        purge_channel_caches()
        parent_conn.send("D")  # "Done"
        process.join(timeout=TIMEOUT)
