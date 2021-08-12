# Will be ignored on Python2 by conftest.py settings

import atexit
import signal
import pytest
from tests.conftest import SubprocessIOC, PV_PREFIX


def aioca_cleanup():
    from aioca import purge_channel_caches, _catools
    # Unregister the aioca atexit handler as it conflicts with the one installed
    # by cothread. If we don't do this we get a seg fault. This is not a problem
    # in production as we won't mix aioca and cothread, but we do mix them in
    # the tests so need to do this.
    atexit.unregister(_catools._catools_atexit)
    # purge the channels before the event loop goes
    purge_channel_caches()


@pytest.fixture
def asyncio_ioc():
    ioc = SubprocessIOC("sim_asyncio_ioc.py")
    yield ioc.proc
    ioc.kill()
    aioca_cleanup()


@pytest.mark.asyncio
async def test_asyncio_ioc(asyncio_ioc):
    import asyncio
    from aioca import caget, caput, camonitor, CANothing, _catools, FORMAT_TIME

    # Start
    assert (await caget(PV_PREFIX + ":UPTIME")).startswith("00:00:0")
    # WAVEFORM
    await caput(PV_PREFIX + ":SINN", 4, wait=True)
    q = asyncio.Queue()
    m = camonitor(PV_PREFIX + ":SIN", q.put, notify_disconnect=True)
    assert len(await asyncio.wait_for(q.get(), 1)) == 4
    # AO
    ao_val = await caget(PV_PREFIX + ":ALARM", format=FORMAT_TIME)
    assert ao_val == 0
    assert ao_val.severity == 3  # INVALID
    assert ao_val.status == 17  # UDF
    await caput(PV_PREFIX + ":ALARM", 3, wait=True)
    await asyncio.sleep(0.1)
    ai_val = await caget(PV_PREFIX + ":AI", format=FORMAT_TIME)
    assert ai_val == 23.45
    assert ai_val.severity == 0
    assert ai_val.status == 0
    await asyncio.sleep(0.8)
    ai_val = await caget(PV_PREFIX + ":AI", format=FORMAT_TIME)
    assert ai_val == 23.45
    assert ai_val.severity == 3
    assert ai_val.status == 7  # STATE_ALARM
    # Check pvaccess works
    from p4p.client.asyncio import Context
    with Context("pva") as ctx:
        assert await ctx.get(PV_PREFIX + ":AI") == 23.45
    # Wait for a bit longer for the print output to flush
    await asyncio.sleep(2)
    # Stop
    out, err = asyncio_ioc.communicate(b"exit\n", timeout=5)
    out = out.decode()
    err = err.decode()
    # Disconnect
    assert isinstance(await asyncio.wait_for(q.get(), 10), CANothing)
    m.close()
    # check closed and output
    assert "%s:SINN.VAL 1024 -> 4" % PV_PREFIX in out
    assert 'update_sin_wf 4' in out
    assert "%s:ALARM.VAL 0 -> 3" % PV_PREFIX in out
    assert 'on_update %s:AO : 3.0' % PV_PREFIX in out
    assert 'async update 3.0 (23.45)' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
    assert '(InteractiveConsole)' in err


@pytest.fixture
def asyncio_ioc_override():
    ioc = SubprocessIOC("sim_asyncio_ioc_override.py")
    yield ioc.proc
    ioc.kill()
    aioca_cleanup()


@pytest.mark.asyncio
async def test_asyncio_ioc_override(asyncio_ioc_override):
    from aioca import caget, caput

    # Gain bo
    assert (await caget(PV_PREFIX + ":GAIN")) == 0
    await caput(PV_PREFIX + ":GAIN", "On", wait=True)
    assert (await caget(PV_PREFIX + ":GAIN")) == 1

    # Stop
    asyncio_ioc_override.send_signal(signal.SIGINT)
    # check closed and output
    out, err = asyncio_ioc_override.communicate()
    out = out.decode()
    err = err.decode()
    # check closed and output
    assert '1' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
