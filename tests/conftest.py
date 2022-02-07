import atexit
import os
import random
import string
import subprocess
import sys

import pytest

# Must import softioc before epicsdbbuilder
from softioc.device_core import RecordLookup
from epicsdbbuilder import ResetRecords

requires_cothread = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Cothread doesn't work on windows"
)

# Default length used to initialise Waveform and longString records.
# Length picked to match string record length, so we can re-use test strings.
WAVEFORM_LENGTH = 40

# Default timeout for many operations across testing
TIMEOUT = 10  # Seconds

def create_random_prefix():
    """Create 12-character random string, for generating unique Device Names"""
    return "".join(random.choice(string.ascii_uppercase) for _ in range(12))

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

def _clear_records():
    # Remove any records created at epicsdbbuilder layer
    ResetRecords()
    # And at pythonSoftIoc level
    # TODO: Remove this hack and use use whatever comes out of
    # https://github.com/dls-controls/pythonSoftIOC/issues/56
    RecordLookup._RecordDirectory.clear()

@pytest.fixture(autouse=True)
def clear_records():
    """Deletes all records before and after every test"""
    _clear_records()
    yield
    _clear_records()

@pytest.fixture(autouse=True)
def enable_code_coverage():
    """Ensure code coverage works as expected for `multiprocesses` tests.
    As its harmless for other types of test, we always run this fixture."""
    try:
        from pytest_cov.embed import cleanup_on_sigterm
    except ImportError:
        pass
    else:
        cleanup_on_sigterm()

def select_and_recv(conn, expected_char = None):
    """Wait for the given Connection to have data to receive, and return it.
    If a character is provided check its correct before returning it.
    This function imports Cothread, and so must NOT be called before any
    multiprocessing sub-processes are spawned."""
    from cothread import select
    rrdy, _, _ = select([conn], [], [], TIMEOUT)
    if rrdy:
        val = conn.recv()
    else:
        pytest.fail("Did not receive expected char before TIMEOUT expired")

    if expected_char:
        assert val == expected_char, \
            "Expected character did not match"

    return val
