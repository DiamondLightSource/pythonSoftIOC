from datetime import datetime
import atexit
import multiprocessing
import os
import random
import string
import subprocess
import sys
from packaging.version import Version
from typing import Any
import pytest

# It is necessary to ensure we always import cothread.catools before aioca as
# doing this import will cause an EPICS context to be created, and it will also
# register an atexit function to delete it.
# If we were to import aioca first it would create an EPICS context, note it has
# created it, then try to delete it in its own atexit function which will
# collide with cothread's attempts to do the same (despite the fact in this
# configuration cothread did not create the context)
if os.name != "nt":
    import cothread.catools

from softioc import builder
from softioc.builder import ClearRecords, SetDeviceName, GetRecordNames

in_records = [
    builder.aIn,
    builder.boolIn,
    builder.longIn,
    builder.int64In,
    builder.mbbIn,
    builder.stringIn,
    builder.WaveformIn,
    builder.longStringIn,
]

requires_cothread = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Cothread doesn't work on windows"
)

# Default length used to initialise Waveform and longString records.
# Length picked to match string record length, so we can re-use test strings.
WAVEFORM_LENGTH = 40

# Default timeout for many operations across testing
TIMEOUT = 20  # Seconds

# Address for multiprocessing Listener/Client pair
ADDRESS = ("localhost", 2345)

def create_random_prefix():
    """Create 12-character random string, for generating unique Device Names"""
    return "".join(random.choice(string.ascii_uppercase) for _ in range(12))

# Can't use logging as it's not multiprocess safe, and
# alternatives are overkill
def log(*args):
    print(datetime.now().strftime("%H:%M:%S"), *args)


class SubprocessIOC:
    def __init__(self, ioc_py):
        self.pv_prefix = create_random_prefix()
        sim_ioc = os.path.join(os.path.dirname(__file__), ioc_py)
        cmd = [sys.executable, sim_ioc, self.pv_prefix]
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def kill(self):
        if self.proc.returncode is None:
            # still running, kill it and print the output
            self.proc.kill()
            out, err = self.proc.communicate(timeout=TIMEOUT)
            print(out.decode())
            print(err.decode())


@pytest.fixture
def cothread_ioc():
    ioc = SubprocessIOC("sim_cothread_ioc.py")
    yield ioc
    ioc.kill()


def aioca_cleanup():
    from aioca import purge_channel_caches, _catools, __version__
    # Unregister the aioca atexit handler as it conflicts with the one installed
    # by cothread. If we don't do this we get a seg fault. This is not a problem
    # in production as we won't mix aioca and cothread, but we do mix them in
    # the tests so need to do this.
    # In aioca 1.8 the atexit function was changed to no longer cause this
    # issue, when coupled with ensuring cothread is always imported first.
    if Version(__version__) < Version("1.8"):
        unregister_func = _catools._Context._destroy_context
        atexit.unregister(unregister_func)

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

def reset_device_name():
    if GetRecordNames().prefix:
        SetDeviceName("")

@pytest.fixture(autouse=True)
def clear_records():
    """Deletes all records before and after every test"""
    ClearRecords()
    reset_device_name()
    yield
    ClearRecords()
    reset_device_name()

@pytest.fixture(autouse=True)
def enable_code_coverage():
    """Ensure code coverage works as expected for `multiprocesses` tests.
    As its harmless for other types of test, we always run this fixture."""
    try:
        from pytest_cov.embed import cleanup_on_sigterm
    except ImportError:
        pass  # Note that pytest_cov.embed no longer exists in pytest_cov>=7.0.0
    else:
        cleanup_on_sigterm()


def select_and_recv(conn, expected_char = None):
    """Wait for the given Connection to have data to receive, and return it.
    If a character is provided check its correct before returning it."""
    # Must use cothread's select if cothread is present, otherwise we'd block
    # processing on all cothread processing. But we don't want to use it
    # unless we have to, as importing cothread can cause issues with forking.
    rrdy: Any = None
    if "cothread" in sys.modules:
        from cothread import select
        rrdy, _, _ = select([conn], [], [], TIMEOUT)
    else:
        # Would use select.select(), but Windows doesn't accept Pipe handles
        # as selectable objects.
        if conn.poll(TIMEOUT):
            rrdy = True

    if rrdy:
        val = conn.recv()
    else:
        pytest.fail("Did not receive expected char before TIMEOUT expired")

    if expected_char:
        assert val == expected_char, \
            "Expected character did not match"

    return val

def get_multiprocessing_context():
    """Tests must use "forkserver" method. If we use "fork" we inherit some
    state from Channel Access from test-to-test, which causes test hangs.

    We cannot use multiprocessing.set_start_method() as it doesn't work inside
    of Pytest."""
    if sys.platform == "win32":
        start_method = "spawn"
    else:
        start_method = "forkserver"
    return multiprocessing.get_context(start_method)
