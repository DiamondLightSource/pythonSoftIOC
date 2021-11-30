import atexit
import os
import random
import string
import subprocess
import sys

import pytest

class SubprocessIOC:
    def __init__(self, ioc_py):
        self.pv_prefix = "".join(
            random.choice(string.ascii_uppercase) for _ in range(12)
        )
        sim_ioc = os.path.join(os.path.dirname(__file__), ioc_py)
        cmd = [sys.executable, sim_ioc, self.pv_prefix]
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def kill(self):
        if self.proc.returncode is None:
            # still running, kill it and print the output
            self.proc.kill()
            out, err = self.proc.communicate()
            print(out.decode())
            print(err.decode())


@pytest.fixture
def cothread_ioc():
    ioc = SubprocessIOC("sim_cothread_ioc.py")
    yield ioc
    ioc.kill()


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
    yield ioc
    ioc.kill()
    aioca_cleanup()


@pytest.fixture
def asyncio_ioc_override():
    ioc = SubprocessIOC("sim_asyncio_ioc_override.py")
    yield ioc
    ioc.kill()
    aioca_cleanup()
