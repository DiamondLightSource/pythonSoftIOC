from typing import List
from softioc import autosave, builder, device_core
import pytest
import threading

DEVICE_NAME = "MY-DEVICE"


@pytest.fixture(autouse=True)
def reset_autosave_setup_teardown():
    default_save_period = autosave.AutosaveConfig.save_period
    default_device_name = autosave.AutosaveConfig.device_name
    default_directory = autosave.AutosaveConfig.directory
    default_enabled = autosave.AutosaveConfig.enabled
    default_tb = autosave.AutosaveConfig.timestamped_backups
    default_pvs = autosave.Autosave._pvs.copy()
    default_state = autosave.Autosave._last_saved_state.copy()
    default_cm_save_fields = autosave._AutosaveContext._fields
    default_instance = autosave._AutosaveContext._instance
    yield
    autosave.AutosaveConfig.save_period = default_save_period
    autosave.AutosaveConfig.device_name = default_device_name
    autosave.AutosaveConfig.directory = default_directory
    autosave.AutosaveConfig.enabled = default_enabled
    autosave.AutosaveConfig.timestamped_backups = default_tb
    autosave.Autosave._pvs = default_pvs
    autosave.Autosave._last_saved_state = default_state
    autosave.Autosave._stop_event = threading.Event()
    autosave._AutosaveContext._fields = default_cm_save_fields
    autosave._AutosaveContext._instance = default_instance


def create_many_threads(tmp_path):
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

def original_test_1(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_2(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_3(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_4(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_5(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_6(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_7(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_8(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")

def original_test_9(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    in_cm_event = threading.Event()

    def create_pv_in_thread(name):
        in_cm_event.wait()
        builder.aOut(name, autosave=False)
    pv_thread_before_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-BEFORE"])
    pv_thread_in_cm = threading.Thread(
        target=create_pv_in_thread, args=["PV-FROM-THREAD-DURING"])
    pv_thread_before_cm.start()
    with autosave.Autosave(["VAL", "EGU"]):
        in_cm_event.set()
        builder.aOut("PV-FROM-CM")
        pv_thread_in_cm.start()
        pv_thread_in_cm.join()
    pv_thread_before_cm.join()

    assert "PV-FROM-THREAD-BEFORE" not in autosave.Autosave._pvs
    assert "PV-FROM-THREAD-DURING" not in autosave.Autosave._pvs
    assert device_core.LookupRecord("PV-FROM-THREAD-BEFORE")
    assert device_core.LookupRecord("PV-FROM-THREAD-DURING")
