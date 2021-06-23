import random
import string
import subprocess
import sys
import os
import signal
import pytest

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12))


if sys.platform.startswith("win"):
    pytest.skip("Cothread doesn't work on windows", allow_module_level=True)


@pytest.fixture
def cothread_ioc():
    sim_ioc = os.path.join(os.path.dirname(__file__), "sim_cothread_ioc.py")
    cmd = [sys.executable, sim_ioc, PV_PREFIX]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    yield proc
    if proc.returncode is None:
        # still running, kill it and print the output
        proc.kill()
        out, err = proc.communicate()
        print(out.decode())
        print(err.decode())



def test_cothread_ioc(cothread_ioc):
    import epicscorelibs.path.cothread
    import cothread
    from cothread.catools import ca_nothing, caget, caput, camonitor

    # Start
    assert caget(PV_PREFIX + ":UPTIME") in ["00:00:00", "00:00:01"]
    # WAVEFORM
    caput(PV_PREFIX + ":SINN", 4, wait=True)
    q = cothread.EventQueue()
    m = camonitor(PV_PREFIX + ":SIN", q.Signal, notify_disconnect=True)
    assert len(q.Wait(1)) == 4
    # STRINGOUT
    assert caget(PV_PREFIX + ":STRINGOUT") == "watevah"
    caput(PV_PREFIX + ":STRINGOUT", "something", wait=True)
    assert caget(PV_PREFIX + ":STRINGOUT") == "something"
    # Stop
    cothread_ioc.send_signal(signal.SIGINT)
    # Disconnect
    assert isinstance(q.Wait(10), ca_nothing)
    m.close()
    # check closed and output
    out, err = cothread_ioc.communicate()
    out = out.decode()
    err = err.decode()
    # check closed and output
    assert "%s:SINN.VAL 1024 -> 4" % PV_PREFIX in out
    assert 'update_sin_wf 4' in out
    assert "%s:STRINGOUT.VAL watevah -> something" % PV_PREFIX in out
    assert 'on_update \'something\'' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
