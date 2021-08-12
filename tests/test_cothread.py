import sys
import signal
from tests.conftest import SubprocessIOC, PV_PREFIX
import pytest


if sys.platform.startswith("win"):
    pytest.skip("Cothread doesn't work on windows", allow_module_level=True)


@pytest.fixture
def cothread_ioc():
    ioc = SubprocessIOC("sim_cothread_ioc.py")
    yield ioc.proc
    ioc.kill()


def test_cothread_ioc(cothread_ioc):
    import cothread
    from cothread.catools import ca_nothing, caget, caput, camonitor

    # Start
    assert caget(PV_PREFIX + ":UPTIME").startswith("00:00:0")
    # WAVEFORM
    caput(PV_PREFIX + ":SINN", 4, wait=True)
    q = cothread.EventQueue()
    m = camonitor(PV_PREFIX + ":SIN", q.Signal, notify_disconnect=True)
    assert len(q.Wait(1)) == 4
    # STRINGOUT
    assert caget(PV_PREFIX + ":STRINGOUT") == "watevah"
    caput(PV_PREFIX + ":STRINGOUT", "something", wait=True)
    assert caget(PV_PREFIX + ":STRINGOUT") == "something"
    # Check pvaccess works
    from p4p.client.cothread import Context
    with Context("pva") as ctx:
        assert ctx.get(PV_PREFIX + ":STRINGOUT") == "something"
    # Wait for a bit longer for the print output to flush
    cothread.Sleep(2)
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
