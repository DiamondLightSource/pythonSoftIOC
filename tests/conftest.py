import os
import random
import string
import subprocess
import sys

if sys.version_info < (3,):
    # Python2 has no asyncio, so ignore these tests
    collect_ignore = [
        "test_asyncio.py", "sim_asyncio_ioc.py", "sim_asyncio_ioc_overide.py"
    ]

PV_PREFIX = "".join(random.choice(string.ascii_uppercase) for _ in range(12))


class SubprocessIOC:
    def __init__(self, ioc_py):
        sim_ioc = os.path.join(os.path.dirname(__file__), ioc_py)
        cmd = [sys.executable, sim_ioc, PV_PREFIX]
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
