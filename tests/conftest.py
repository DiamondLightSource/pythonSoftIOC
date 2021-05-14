import sys

if sys.version_info < (3,):
    # Python2 has no asyncio, so ignore these tests
    collect_ignore = ["test_asyncio.py", "sim_asyncio_ioc.py"]
