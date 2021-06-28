# Will be ignored on Python2 by conftest.py settings

import random
import string
import subprocess
import sys
import os
import atexit
import pytest

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12))


@pytest.fixture
def asyncio_ioc():
    sim_ioc = os.path.join(os.path.dirname(__file__), "sim_asyncio_ioc.py")
    cmd = [sys.executable, sim_ioc, PV_PREFIX]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    yield proc
    # purge the channels before the event loop goes
    from aioca import purge_channel_caches
    purge_channel_caches()
    if proc.returncode is None:
        # still running, kill it and print the output
        proc.kill()
        out, err = proc.communicate()
        print(out.decode())
        print(err.decode(), file=sys.stderr)


@pytest.mark.asyncio
async def test_asyncio_ioc(asyncio_ioc):
    import asyncio
    from aioca import caget, caput, camonitor, CANothing, _catools
    # Unregister the atexit handler as it conflicts with cothread
    atexit.unregister(_catools._catools_atexit)

    # Start
    assert await caget(PV_PREFIX + ":UPTIME") in [
        "00:00:00", "00:00:01", "00:00:02", "00:00:03"
    ]
    # WAVEFORM
    await caput(PV_PREFIX + ":SINN", 4, wait=True)
    q = asyncio.Queue()
    m = camonitor(PV_PREFIX + ":SIN", q.put, notify_disconnect=True)
    assert len(await asyncio.wait_for(q.get(), 1)) == 4
    # AO
    assert await caget(PV_PREFIX + ":AO2") == 12.45
    await caput(PV_PREFIX + ":AO2", 3.56, wait=True)
    await asyncio.sleep(0.1)
    assert await caget(PV_PREFIX + ":AI") == 12.34
    await asyncio.sleep(0.8)
    assert await caget(PV_PREFIX + ":AI") == 3.56
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
    assert "%s:AO2.VAL 12.45 -> 3.56" % PV_PREFIX in out
    assert 'async update 3.56' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
    assert '(InteractiveConsole)' in err
