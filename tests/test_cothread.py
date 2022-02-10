import signal

from multiprocessing.connection import Listener

from conftest import requires_cothread, ADDRESS, select_and_recv

@requires_cothread
def test_cothread_ioc(cothread_ioc):
    import cothread
    from cothread.catools import ca_nothing, caget, caput, camonitor

    pre = cothread_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:

        select_and_recv(conn, "R")  # "Ready"

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

        conn.send("D")  # "Done"

        select_and_recv(conn, "D")  # "Done"

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
    try:
        assert "%s:SINN.VAL 1024 -> 4" % pre in out
        assert 'update_sin_wf 4' in out
        assert "%s:STRINGOUT.VAL watevah -> something" % pre in out
        assert 'on_update \'something\'' in out
        assert 'Starting iocInit' in err
        assert 'iocRun: All initialization complete' in err
    except Exception:
        # Useful printing for when things go wrong!
        print("Out:", out)
        print("Err:", err)
        raise
