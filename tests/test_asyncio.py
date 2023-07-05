import asyncio
import pytest
import sys

from multiprocessing.connection import Listener

from conftest import requires_cothread, ADDRESS, select_and_recv

from softioc.asyncio_dispatcher import AsyncioDispatcher

@pytest.mark.asyncio
async def test_asyncio_ioc(asyncio_ioc):
    import asyncio
    from aioca import caget, caput, camonitor, CANothing, FORMAT_TIME

    pre = asyncio_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:

        select_and_recv(conn, "R")  # "Ready"

        # Start
        assert (await caget(pre + ":UPTIME")).startswith("00:00:0")
        # WAVEFORM
        await caput(pre + ":SINN", 4, wait=True)
        q = asyncio.Queue()
        m = camonitor(pre + ":SIN", q.put, notify_disconnect=True)
        assert len(await asyncio.wait_for(q.get(), 1)) == 4
        # AO
        ao_val = await caget(pre + ":ALARM", format=FORMAT_TIME)
        assert ao_val == 0
        assert ao_val.severity == 3  # INVALID
        assert ao_val.status == 17  # UDF

        ai_val = await caget(pre + ":AI", format=FORMAT_TIME)
        assert ai_val == 23.45
        assert ai_val.severity == 0
        assert ai_val.status == 0

        await caput(pre + ":ALARM", 3, wait=True)

        await caput(pre + ":NAME-CALLBACK", 12, wait=True)

        # Confirm the ALARM callback has completed
        select_and_recv(conn, "C")  # "Complete"

        ai_val = await caget(pre + ":AI", format=FORMAT_TIME)
        assert ai_val == 23.45
        assert ai_val.severity == 3
        assert ai_val.status == 7  # STATE_ALARM
        # Check pvaccess works
        from p4p.client.asyncio import Context
        with Context("pva") as ctx:
            assert await ctx.get(pre + ":AI") == 23.45
            long_pv = pre + ":AVERYLONGRECORDSUFFIXTOMAKELONGPV"
            long_str = "A long string that is more than 40 characters long"
            assert await ctx.get(long_pv) == long_str
            assert await ctx.get(long_pv + ".NAME") == long_pv
            await ctx.put(pre + ":LONGSTRING", long_str)
            assert await ctx.get(pre + ":LONGSTRING") == long_str

        conn.send("D")  # "Done"
        select_and_recv(conn, "D")  # "Done"

    # Stop
    out, err = asyncio_ioc.proc.communicate(b"exit\n", timeout=5)
    out = out.decode()
    err = err.decode()
    # Disconnect
    assert isinstance(await asyncio.wait_for(q.get(), 10), CANothing)
    m.close()
    # check closed and output
    try:
        assert "%s:SINN.VAL 1024 -> 4" % pre in out
        assert 'update_sin_wf 4' in out
        assert "%s:ALARM.VAL 0 -> 3" % pre in out
        assert 'on_update %s:AO : 3.0' % pre in out
        assert 'async update 3.0 (23.45)' in out
        assert "%s:NAME-CALLBACK value 12" % pre in out
        assert 'Starting iocInit' in err
        assert 'iocRun: All initialization complete' in err
    except Exception:
        # Useful printing for when things go wrong!
        print("Out:", out)
        print("Err:", err)
        raise


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform.startswith("darwin"),
    reason="devIocStats reboot doesn't work on MacOS")
async def test_asyncio_ioc_override(asyncio_ioc_override):
    from aioca import caget, caput

    with Listener(ADDRESS) as listener, listener.accept() as conn:

        select_and_recv(conn, "R")  # "Ready"

        # Gain bo
        pre = asyncio_ioc_override.pv_prefix
        assert (await caget(pre + ":GAIN")) == 0
        await caput(pre + ":GAIN", "On", wait=True)
        assert (await caget(pre + ":GAIN")) == 1

        # Stop
        await caput(pre + ":SYSRESET", 1)

        conn.send("D")  # "Done"
        select_and_recv(conn, "D")  # "Done"

    # check closed and output
    out, err = asyncio_ioc_override.proc.communicate(timeout=5)
    out = out.decode()
    err = err.decode()
    # check closed and output
    try:
        assert '1' in out
        assert 'Starting iocInit' in err
        assert 'iocRun: All initialization complete' in err
        assert 'IOC reboot started' in err
    except Exception:
        # Useful printing for when things go wrong!
        print("Out:", out)
        print("Err:", err)
        raise

def test_asyncio_dispatcher_event_loop():
    """Test that passing a non-running event loop to the AsyncioDispatcher
    raises an exception"""
    event_loop = asyncio.get_event_loop()
    with pytest.raises(ValueError):
        AsyncioDispatcher(loop=event_loop)
