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


@pytest.fixture
def existing_autosave_dir(tmp_path):
    state = {
        "SAVED-AO": 20.0,
        "SAVED-AI": 20.0,
        "SAVED-BO": 1,
        "SAVED-BI": 1,
        "SAVED-LONGIN": 20,
        "SAVED-LONGOUT": 20,
        "SAVED-INT64IN": 100,
        "SAVED-INT64OUT": 100,
        "SAVED-MBBI": 15,
        "SAVED-MBBO": 15,
        "SAVED-STRINGIN": "test string in",
        "SAVED-STRINGOUT": "test string out",
        "SAVED-LONGSTRINGIN": "test long string in",
        "SAVED-LONGSTRINGOUT": "test long string out",
        "SAVED-ACTION": 1,
        "SAVED-WAVEFORMIN": [1, 2, 3, 4],
        "SAVED-WAVEFORMOUT": [1, 2, 3, 4],
        "SAVED-WAVEFORMIN-STRINGS": ["test", "waveform", "strings"],
        "SAVED-WAVEFORMOUT-STRINGS": ["test", "waveform", "strings"],
    }
    with open(tmp_path / f"{DEVICE_NAME}.softsav", "w") as f:
        yaml.dump(state, f, indent=4)
    with open(tmp_path / f"{DEVICE_NAME}.softsav.bu", "w") as f:
        yaml.dump({"OUT-OF-DATE-KEY": "out of date value"}, f, indent=4)
    return tmp_path


def test_configure(tmp_path):
    assert autosave.AutosaveConfig.enabled is False
    autosave.configure(tmp_path, DEVICE_NAME)
    assert autosave.AutosaveConfig.device_name == DEVICE_NAME
    assert autosave.AutosaveConfig.directory == tmp_path
    assert autosave.AutosaveConfig.enabled is True
    assert autosave.AutosaveConfig.timestamped_backups is True


def test_autosave_defaults():
    assert autosave.Autosave._pvs == {}
    assert autosave.Autosave._last_saved_state == {}
    assert isinstance(autosave.Autosave._stop_event, threading.Event)
    assert not autosave.Autosave._stop_event.is_set()
    assert autosave.AutosaveConfig.save_period == 30.0
    assert autosave.AutosaveConfig.device_name is None
    assert autosave.AutosaveConfig.directory is None
    assert autosave.AutosaveConfig.enabled is False
    assert autosave.AutosaveConfig.timestamped_backups is True


def test_configure_dir_doesnt_exist(tmp_path):
    DEVICE_NAME = "MY_DEVICE"
    builder.aOut("MY-RECORD", autosave=True)
    with pytest.raises(FileNotFoundError):
        autosave.configure(tmp_path / "subdir-doesnt-exist", DEVICE_NAME)


def test_returns_if_init_called_before_configure():
    autosave.Autosave()
    assert autosave.AutosaveConfig.enabled is False


def test_all_record_types_saveable(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)

    number_types = [
        "aIn",
        "aOut",
        "boolIn",
        "boolOut",
        "longIn",
        "longOut",
        "int64In",
        "int64Out",
        "mbbIn",
        "mbbOut",
        "Action",
    ]
    string_types = ["stringIn", "stringOut", "longStringIn", "longStringOut"]
    waveform_types = ["WaveformIn", "WaveformOut"]
    for pv_type in number_types:
        pv = getattr(builder, pv_type)(pv_type, autosave=True)
    for pv_type in string_types:
        pv = getattr(builder, pv_type)(pv_type, autosave=True)
        pv.set("test string")
    for pv_type in waveform_types:
        getattr(builder, pv_type)(pv_type, numpy.zeros((100)), autosave=True)
        getattr(builder, pv_type)(
            f"{pv_type}_of_chars", "test waveform string", autosave=True
        )
        getattr(builder, pv_type)(
            f"{pv_type}_of_strings", ["array", "of", "strings"], autosave=True
        )

    autosaver = autosave.Autosave()
    autosaver._save()

    with open(tmp_path / f"{DEVICE_NAME}.softsav", "r") as f:
        saved = yaml.full_load(f)
    for pv_type in number_types + string_types + waveform_types:
        assert pv_type in saved


def test_can_save_fields(tmp_path):
    builder.aOut("SAVEVAL", autosave=["VAL", "DISA"])
    builder.aOut("DONTSAVEVAL", autosave=["SCAN"])
    # we need to patch get_field as we can't call builder.LoadDatabase()
    # and softioc.iocInit() in unit tests
    with patch(
        "softioc.device.ProcessDeviceSupportCore.get_field", return_value="0"
    ):
        autosave.configure(tmp_path, DEVICE_NAME)
        autosaver = autosave.Autosave()
        assert "SAVEVAL" in autosaver._pvs
        assert "SAVEVAL.DISA" in autosaver._pvs
        assert "DONTSAVEVAL" not in autosaver._pvs
        assert "DONTSAVEVAL.SCAN" in autosaver._pvs
        autosaver._save()
        with open(tmp_path / f"{DEVICE_NAME}.softsav", "r") as f:
            saved = yaml.full_load(f)
        assert "SAVEVAL" in saved
        assert "SAVEVAL.DISA" in saved
        assert "DONTSAVEVAL" not in saved
        assert "DONTSAVEVAL.SCAN" in saved


def test_stop_event(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    builder.aOut("DUMMYRECORD", autosave=True)
    worker = threading.Thread(
        target=autosave.Autosave._loop,
    )
    try:
        worker.daemon = True
        worker.start()
        assert not autosave.Autosave._stop_event.is_set()
        assert worker.is_alive()
        autosave.Autosave._stop()
        assert autosave.Autosave._stop_event.is_set()
    finally:
        worker.join(timeout=1)


@pytest.mark.parametrize(
    "timestamped,regex",
    [
        (False, r"^" + DEVICE_NAME + r"\.softsav_[0-9]{6}-[0-9]{6}$"),
        (True, r"^" + DEVICE_NAME + r"\.softsav\.bu$"),
    ],
)
def test_backup_on_load(existing_autosave_dir, timestamped, regex):
    autosave.configure(
        existing_autosave_dir, DEVICE_NAME, timestamped_backups=timestamped
    )
    # backup only performed if there are any pvs to save
    builder.aOut("SAVED-AO", autosave=True)
    autosave.load_autosave()
    backup_files = list(existing_autosave_dir.glob("*.softsav_*"))
    # assert backup is <name>.softsav_yymmdd-HHMMSS or <name>.softsav.bu
    any(re.match(regex, file.name) for file in backup_files)
    if not timestamped:
        # test that existing .bu file gets overwritten
        with open(existing_autosave_dir / f"{DEVICE_NAME}.softsav.bu") as f:
            state = yaml.full_load(f)
            assert "OUT-OF-DATE-KEY" not in state
            assert "SAVED-AO" in state


def test_autosave_key_names(tmp_path):
    builder.aOut("DEFAULTNAME", autosave=True)
    builder.aOut("DEFAULTNAMEAFTERPREFIXSET", autosave=True)
    autosave.configure(tmp_path, DEVICE_NAME)
    autosaver = autosave.Autosave()
    autosaver._save()
    with open(tmp_path / f"{DEVICE_NAME}.softsav", "r") as f:
        saved = yaml.full_load(f)
    assert "DEFAULTNAME" in saved
    assert "DEFAULTNAMEAFTERPREFIXSET" in saved


def test_context_manager(tmp_path):
    builder.aOut("MANUAL", autosave=["VAL", "EGU"])
    with autosave.Autosave(["VAL", "PINI"]):
        builder.aOut("AUTOMATIC")
        builder.aOut(
            "AUTOMATIC-EXTRA-FIELD", autosave=["SCAN"]
        )
    autosave.configure(tmp_path, DEVICE_NAME)
    with patch(
        "softioc.device.ProcessDeviceSupportCore.get_field", return_value="0"
    ):
        autosaver = autosave.Autosave()
        autosaver._save()
        with open(tmp_path / f"{DEVICE_NAME}.softsav", "r") as f:
            saved = yaml.full_load(f)
        assert "MANUAL" in saved
        assert "MANUAL.EGU" in saved
        assert "AUTOMATIC" in saved
        assert "AUTOMATIC.PINI" in saved
        assert "AUTOMATIC-EXTRA-FIELD" in saved
        assert "AUTOMATIC-EXTRA-FIELD.SCAN" in saved
        assert "AUTOMATIC-EXTRA-FIELD.PINI" in saved


def check_all_record_types_load_properly(device_name, autosave_dir, conn):
    autosave.configure(autosave_dir, device_name)
    pv_aOut = builder.aOut("SAVED-AO", autosave=True)
    pv_aIn = builder.aIn("SAVED-AI", autosave=True)
    pv_boolOut = builder.boolOut("SAVED-BO", autosave=True)
    pv_boolIn = builder.boolIn("SAVED-BI", autosave=True)
    pv_longIn = builder.longIn("SAVED-LONGIN", autosave=True)
    pv_longOut = builder.longOut("SAVED-LONGOUT", autosave=True)
    pv_int64In = builder.int64In("SAVED-INT64IN", autosave=True)
    pv_int64Out = builder.int64Out("SAVED-INT64OUT", autosave=True)
    pv_mbbIn = builder.mbbIn("SAVED-MBBI", autosave=True)
    pv_mbbOut = builder.mbbOut("SAVED-MBBO", autosave=True)
    pv_stringIn = builder.stringIn("SAVED-STRINGIN", autosave=True)
    pv_stringOut = builder.stringOut("SAVED-STRINGOUT", autosave=True)
    pv_longStringIn = builder.longStringIn("SAVED-LONGSTRINGIN", autosave=True)
    pv_longStringOut = builder.longStringOut(
        "SAVED-LONGSTRINGOUT", autosave=True
    )
    pv_Action = builder.Action("SAVED-ACTION", autosave=True)
    pv_WaveformIn = builder.WaveformIn(
        "SAVED-WAVEFORMIN", numpy.zeros((4)), autosave=True
    )
    pv_WaveformOut = builder.WaveformOut(
        "SAVED-WAVEFORMOUT", numpy.zeros((4)), autosave=True
    )
    pv_WaveformIn_strings = builder.WaveformIn(
        "SAVED-WAVEFORMIN-STRINGS",
        ["initial", "waveform", "strings"],
        autosave=True,
    )
    pv_WaveformOut_strings = builder.WaveformOut(
        "SAVED-WAVEFORMOUT-STRINGS",
        ["initial", "waveform", "strings"],
        autosave=True,
    )
    assert pv_aOut.get() == 0.0
    assert pv_aIn.get() == 0.0
    assert pv_boolOut.get() == 0
    assert pv_boolIn.get() == 0
    assert pv_longIn.get() == 0
    assert pv_longOut.get() == 0
    assert pv_int64In.get() == 0
    assert pv_int64Out.get() == 0
    assert pv_mbbIn.get() == 0
    assert pv_mbbOut.get() == 0
    assert pv_stringIn.get() == ""
    assert pv_stringOut.get() == ""
    assert pv_longStringIn.get() == ""
    assert pv_longStringOut.get() == ""
    assert pv_Action.get() == 0
    assert (pv_WaveformIn.get() == numpy.array([0, 0, 0, 0])).all()
    assert (pv_WaveformOut.get() == numpy.array([0, 0, 0, 0])).all()
    assert pv_WaveformIn_strings.get() == ["initial", "waveform", "strings"]
    assert pv_WaveformOut_strings.get() == ["initial", "waveform", "strings"]
    # load called automatically when LoadDatabase() called
    builder.LoadDatabase()
    assert pv_aOut.get() == 20.0
    assert pv_aIn.get() == 20.0
    assert pv_boolOut.get() == 1
    assert pv_boolIn.get() == 1
    assert pv_longIn.get() == 20
    assert pv_longOut.get() == 20
    assert pv_int64In.get() == 100
    assert pv_int64Out.get() == 100
    assert pv_mbbIn.get() == 15
    assert pv_mbbOut.get() == 15
    assert pv_stringIn.get() == "test string in"
    assert pv_stringOut.get() == "test string out"
    assert pv_longStringIn.get() == "test long string in"
    assert pv_longStringOut.get() == "test long string out"
    assert pv_Action.get() == 1
    assert (pv_WaveformIn.get() == numpy.array([1, 2, 3, 4])).all()
    assert (pv_WaveformOut.get() == numpy.array([1, 2, 3, 4])).all()
    assert pv_WaveformIn_strings.get() == ["test", "waveform", "strings"]
    assert pv_WaveformOut_strings.get() == ["test", "waveform", "strings"]
    conn.send("D")  # "Done"


def test_actual_ioc_load(existing_autosave_dir):
    ctx = get_multiprocessing_context()
    parent_conn, child_conn = ctx.Pipe()
    ioc_process = ctx.Process(
        target=check_all_record_types_load_properly,
        args=(DEVICE_NAME, existing_autosave_dir, child_conn),
    )
    ioc_process.start()
    # If we never receive D it probably means an assert failed
    select_and_recv(parent_conn, "D")


def check_all_record_types_save_properly(device_name, autosave_dir, conn):
    autosave.configure(autosave_dir, device_name, save_period=1)
    builder.aOut("aOut", autosave=True, initial_value=20.0)
    builder.aIn("aIn", autosave=True, initial_value=20.0)
    builder.boolOut("boolOut", autosave=True, initial_value=1)
    builder.boolIn("boolIn", autosave=True, initial_value=1)
    builder.longIn("longIn", autosave=True, initial_value=20)
    builder.longOut("longOut", autosave=True, initial_value=20)
    builder.int64In("int64In", autosave=True, initial_value=100)
    builder.int64Out("int64Out", autosave=True, initial_value=100)
    builder.mbbIn("mbbIn", autosave=True, initial_value=15)
    builder.mbbOut("mbbOut", autosave=True, initial_value=15)
    builder.stringIn("stringIn", autosave=True, initial_value="test string in")
    builder.stringOut(
        "stringOut", autosave=True, initial_value="test string out"
    )
    builder.longStringIn(
        "longStringIn", autosave=True, initial_value="test long string in"
    )
    builder.longStringOut(
        "longStringOut", autosave=True, initial_value="test long string out"
    )
    builder.Action("Action", autosave=True, initial_value=1)
    builder.WaveformIn("WaveformIn", [1, 2, 3, 4], autosave=True)
    builder.WaveformOut("WaveformOut", [1, 2, 3, 4], autosave=True)
    builder.LoadDatabase()
    dispatcher = asyncio_dispatcher.AsyncioDispatcher()
    softioc.iocInit(dispatcher)
    # wait long enough to ensure one save has occurred
    time.sleep(2)
    with open(autosave_dir / f"{device_name}.softsav", "r") as f:
        saved = yaml.full_load(f)
    assert saved["aOut"] == 20.0
    assert saved["aIn"] == 20.0
    assert saved["boolOut"] == 1
    assert saved["boolIn"] == 1
    assert saved["longIn"] == 20
    assert saved["longOut"] == 20
    assert saved["int64In"] == 100
    assert saved["int64Out"] == 100
    assert saved["mbbIn"] == 15
    assert saved["mbbOut"] == 15
    assert saved["stringIn"] == "test string in"
    assert saved["stringOut"] == "test string out"
    assert saved["longStringIn"] == "test long string in"
    assert saved["longStringOut"] == "test long string out"
    assert saved["Action"] == 1
    assert (saved["WaveformIn"] == numpy.array([1, 2, 3, 4])).all()
    assert (saved["WaveformOut"] == numpy.array([1, 2, 3, 4])).all()
    autosave.Autosave._stop()
    # force autosave thread to stop to ensure pytest exits
    conn.send("D")


def test_actual_ioc_save(tmp_path):
    ctx = get_multiprocessing_context()
    parent_conn, child_conn = ctx.Pipe()
    ioc_process = ctx.Process(
        target=check_all_record_types_save_properly,
        args=(DEVICE_NAME, tmp_path, child_conn),
    )
    ioc_process.start()
    # If we never receive D it probably means an assert failed
    select_and_recv(parent_conn, "D")


def check_autosave_field_names_contain_device_prefix(
    device_name, tmp_path, conn
):
    autosave.configure(tmp_path, device_name, save_period=1)
    builder.aOut("BEFORE", autosave=["VAL", "EGU"])
    builder.SetDeviceName(device_name)
    builder.aOut("AFTER", autosave=["VAL", "EGU"])
    builder.LoadDatabase()
    dispatcher = asyncio_dispatcher.AsyncioDispatcher()
    softioc.iocInit(dispatcher)
    time.sleep(2)
    with open(tmp_path / f"{device_name}.softsav", "r") as f:
        saved = yaml.full_load(f)
    assert "BEFORE" in saved.keys()
    assert f"{device_name}:AFTER" in saved.keys()
    autosave.Autosave._stop()
    conn.send("D")


def test_autosave_field_names_contain_device_prefix(tmp_path):
    ctx = get_multiprocessing_context()
    parent_conn, child_conn = ctx.Pipe()
    ioc_process = ctx.Process(
        target=check_autosave_field_names_contain_device_prefix,
        args=(DEVICE_NAME, tmp_path, child_conn),
    )
    ioc_process.start()
    # If we never receive D it probably means an assert failed
    select_and_recv(parent_conn, "D")

def test_context_manager_thread_safety(tmp_path):
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

def test_nested_context_managers_raises(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    with autosave.Autosave(["SCAN"]):
        with pytest.raises(RuntimeError):
            with autosave.Autosave(False):
                builder.aOut("MY-PV")
        with pytest.raises(RuntimeError):
            autosave.Autosave()

def test_autosave_arguments(tmp_path):
    autosave.configure(tmp_path, DEVICE_NAME)
    builder.aOut("TRUE", autosave=True)
    builder.aOut("FIELDS", autosave=["LOPR", "HOPR"])
    builder.aOut("FALSE", autosave=False)
    builder.aOut("SINGLE-FIELD", autosave="EGU")
    builder.aOut("AUTO-VAL", autosave="VAL")
    assert set(autosave.Autosave._pvs) == {
        "TRUE", "FIELDS.LOPR", "FIELDS.HOPR", "SINGLE-FIELD.EGU", "AUTO-VAL"}
    autosave.Autosave._pvs = {}
    builder.ClearRecords()
    with autosave.Autosave():  # True by default
        builder.aOut("AUTO-TRUE", autosave=False)
        builder.aOut("FIELDS", autosave=["LOPR", "HOPR"])
    assert set(autosave.Autosave._pvs) == {
        "FIELDS", "FIELDS.LOPR", "FIELDS.HOPR"}
    autosave.Autosave._pvs = {}
    builder.ClearRecords()
    with autosave.Autosave(["EGU"]):
        builder.aOut("AUTO-FALSE")
        builder.aOut("FIELDS", autosave=["PINI"])
    assert set(autosave.Autosave._pvs) == {
        "AUTO-FALSE.EGU", "FIELDS.EGU", "FIELDS.PINI"}
    autosave.Autosave._pvs = {}
    builder.ClearRecords()
    with autosave.Autosave(False):
        builder.aOut("AUTO-DEFAULT")
        builder.aOut("AUTO-TRUE", autosave=True)
    assert set(autosave.Autosave._pvs) == {"AUTO-TRUE"}
    autosave.Autosave._pvs = {}
    builder.ClearRecords()
    with autosave.Autosave("LOPR"):  # single field
        builder.aOut("FIELDS", autosave="HOPR")
    assert set(autosave.Autosave._pvs) == {"FIELDS.HOPR", "FIELDS.LOPR"}
