from typing import List
from conftest import get_multiprocessing_context, select_and_recv
from softioc import autosave, builder, softioc, device_core, asyncio_dispatcher
from unittest.mock import patch
import pytest
import threading
import numpy
import re
import yaml
import time

DEVICE_NAME = "MY-DEVICE"



def test_context_manager_thread_safety(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)

    threads: List[threading.Thread] = []
    for i in range(1,50):
        threads.append( threading.Thread(
            target=create_pv_in_thread, args=[f"PV-FROM-THREAD-BEFORE{i}"]))

    [x.start() for x in threads]
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
    [x.join() for x in threads]
