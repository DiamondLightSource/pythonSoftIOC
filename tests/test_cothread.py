import sys
import signal
import pytest


if sys.platform.startswith("win"):
    pytest.skip("Cothread doesn't work on windows", allow_module_level=True)



def test_cothread_ioc(cothread_ioc):
    import cothread
    from cothread.catools import ca_nothing, caget, caput, camonitor

    pre = cothread_ioc.pv_prefix
    # Start
    assert caget(pre + ":UPTIME").startswith("00:00:0")
    # WAVEFORM
    caput(pre + ":SINN", 4, wait=True)
    q = cothread.EventQueue()
    m = camonitor(pre + ":SIN", q.Signal, notify_disconnect=True)
    assert len(q.Wait(1)) == 4
    # STRINGOUT
    assert caget(pre + ":STRINGOUT") == "watevah"
    caput(pre + ":STRINGOUT", "something", wait=True)
    assert caget(pre + ":STRINGOUT") == "something"
    # Check pvaccess works
    from p4p.client.cothread import Context
    with Context("pva") as ctx:
        assert ctx.get(pre + ":STRINGOUT") == "something"
    # Wait for a bit longer for the print output to flush
    cothread.Sleep(2)
    # Stop
    cothread_ioc.proc.send_signal(signal.SIGINT)
    # Disconnect
    assert isinstance(q.Wait(10), ca_nothing)
    m.close()
    # check closed and output
    out, err = cothread_ioc.proc.communicate()
    out = out.decode()
    err = err.decode()
    # check closed and output
    assert "%s:SINN.VAL 1024 -> 4" % pre in out
    assert 'update_sin_wf 4' in out
    assert "%s:STRINGOUT.VAL watevah -> something" % pre in out
    assert 'on_update \'something\'' in out
    assert 'Starting iocInit' in err
    assert 'iocRun: All initialization complete' in err
