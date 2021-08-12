# Will be ignored on Python2 by conftest.py settings

import pytest


@pytest.mark.asyncio
async def test_asyncio_ioc(asyncio_ioc):
    import asyncio
    from aioca import caget, caput, camonitor, CANothing, FORMAT_TIME

    # Start
    pre = asyncio_ioc.pv_prefix
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
    await caput(pre + ":ALARM", 3, wait=True)
    await asyncio.sleep(0.1)
    ai_val = await caget(pre + ":AI", format=FORMAT_TIME)
    assert ai_val == 23.45
    assert ai_val.severity == 0
    assert ai_val.status == 0
    await asyncio.sleep(0.8)
    ai_val = await caget(pre + ":AI", format=FORMAT_TIME)
    assert ai_val == 23.45
    assert ai_val.severity == 3
    assert ai_val.status == 7  # STATE_ALARM
    # Check pvaccess works
    from p4p.client.asyncio import Context
    with Context("pva") as ctx:
        assert await ctx.get(pre + ":AI") == 23.45
    # Wait for a bit longer for the print output to flush
    await asyncio.sleep(2)
    # Stop
    out, err = asyncio_ioc.proc.communicate(b"exit\n", timeout=5)
    out = out.decode()
    err = err.decode()
    # Disconnect
    assert isinstance(await asyncio.wait_for(q.get(), 10), CANothing)
    m.close()
    # check closed and output
    assert "%s:SINN.VAL 1024 -> 4" % pre in out
    assert 'update_sin_wf 4' in out
    assert "%s:ALARM.VAL 0 -> 3" % pre in out
    assert 'on_update %s:AO : 3.0' % pre in out
    assert 'async update 3.0 (23.45)' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
    assert '(InteractiveConsole)' in err


@pytest.mark.asyncio
async def test_asyncio_ioc_override(asyncio_ioc_override):
    from aioca import caget, caput

    # Gain bo
    pre = asyncio_ioc_override.pv_prefix
    assert (await caget(pre + ":GAIN")) == 0
    await caput(pre + ":GAIN", "On", wait=True)
    assert (await caget(pre + ":GAIN")) == 1

    # Stop
    await caput(pre + ":SYSRESET", 1)
    # check closed and output
    out, err = asyncio_ioc_override.proc.communicate()
    out = out.decode()
    err = err.decode()
    # check closed and output
    assert '1' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
    assert 'IOC reboot started' in err
