from softioc import autosave, builder
from pathlib import Path
from unittest.mock import patch
import pytest
import threading
import shutil
import numpy
import re
import yaml

DEVICE_NAME = "MY-DEVICE"


@pytest.fixture(autouse=True)
def reset_autosave_setup_teardown():
    default_pvs = autosave.Autosave._pvs.copy()
    default_state = autosave.Autosave._last_saved_state.copy()
    default_save_period = autosave.Autosave.save_period
    default_device_name = autosave.Autosave.device_name
    default_directory = autosave.Autosave.directory
    default_enabled = autosave.Autosave.enabled
    default_bol = autosave.Autosave.backup_on_load
    yield
    autosave.Autosave._pvs = default_pvs
    autosave.Autosave._last_saved_state = default_state
    autosave.Autosave._stop_event = threading.Event()
    autosave.Autosave.save_period = default_save_period
    autosave.Autosave.device_name = default_device_name
    autosave.Autosave.directory = default_directory
    autosave.Autosave.enabled = default_enabled
    autosave.Autosave.backup_on_load = default_bol
    if builder.GetRecordNames().prefix:  # reset device name to empty if set
        builder.SetDeviceName("")


@pytest.fixture
def existing_autosave_dir(tmp_path):
    state = {"ALREADYSAVED": 20.0}
    with open(tmp_path / f"{DEVICE_NAME}.softsav", "w") as f:
        yaml.dump(state, f, indent=4)
    return tmp_path


def test_configure(tmp_path):
    assert autosave.Autosave.enabled is False
    autosave.configure(tmp_path, DEVICE_NAME)
    assert autosave.Autosave.device_name == DEVICE_NAME
    assert autosave.Autosave.directory == tmp_path
    assert autosave.Autosave.enabled is True


def test_autosave_defaults():
    assert autosave.Autosave._pvs == {}
    assert autosave.Autosave._last_saved_state == {}
    assert isinstance(autosave.Autosave._stop_event, threading.Event)
    assert not autosave.Autosave._stop_event.is_set()
    assert autosave.Autosave.save_period == 30.0
    assert autosave.Autosave.device_name is None
    assert autosave.Autosave.directory is None
    assert autosave.Autosave.enabled is False
    assert autosave.Autosave.backup_on_load is False


def test_configure_dir_doesnt_exist(tmp_path):
    DEVICE_NAME = "MY_DEVICE"
    autosave.configure(tmp_path / "subdir-doesnt-exist", DEVICE_NAME)
    with pytest.raises(FileNotFoundError):
        autosave.Autosave()


def test_returns_if_init_called_before_configure():
    autosave.Autosave()
    assert autosave.Autosave.enabled is False


def test_all_record_types_saveable(tmp_path):
    builder.SetDeviceName(DEVICE_NAME)
    autosave.configure(tmp_path, DEVICE_NAME)

    number_types = ["aIn", "aOut", "boolIn", "boolOut", "longIn", "longOut",
                    "int64In", "int64Out", "mbbIn", "mbbOut", "Action"]
    string_types = ["stringIn", "stringOut", "longStringIn", "longStringOut"]
    waveform_types = ["WaveformIn", "WaveformOut"]
    for pv_type in number_types:
        pv = getattr(builder, pv_type)(pv_type, autosave=True)
    for pv_type in string_types:
        pv = getattr(builder, pv_type)(pv_type, autosave=True)
        pv.set("test string")
    for pv_type in waveform_types:
        getattr(builder, pv_type)(pv_type, numpy.zeros((100)), autosave=True)
    autosaver = autosave.Autosave()
    autosaver._save()

    with open(tmp_path / f"{DEVICE_NAME}.softsav", "r") as f:
        saved = yaml.full_load(f)
    for pv_type in number_types + string_types + waveform_types:
        assert pv_type in saved


def test_can_save_fields(tmp_path):
    builder.SetDeviceName(DEVICE_NAME)
    builder.aOut("SAVEVAL", autosave=True, autosave_fields=["DISA"])
    builder.aOut("DONTSAVEVAL", autosave_fields=["SCAN"])
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
    autosaver = autosave.Autosave()
    worker = threading.Thread(
        target=autosaver.loop,
    )
    try:
        worker.daemon = True
        worker.start()
        assert not autosaver._stop_event.is_set()
        assert worker.is_alive()
        autosaver.stop()
        assert autosaver._stop_event.is_set()
    finally:
        worker.join(timeout=1)


def test_load_autosave(existing_autosave_dir):
    builder.SetDeviceName(DEVICE_NAME)
    autosave.configure(existing_autosave_dir, DEVICE_NAME, backup=False)
    pv = builder.aOut("ALREADYSAVED", autosave=True)
    assert pv.get() == 0.0
    autosave.load_autosave()
    assert pv.get() == 20.0


def test_backup_on_load(existing_autosave_dir):
    autosave.configure(existing_autosave_dir, DEVICE_NAME, backup=True)
    # backup only performed if there are any pvs to save
    builder.aOut("ALREADYSAVED", autosave=True)
    autosave.load_autosave()
    backup_files = list(existing_autosave_dir.glob("*.softsav_*"))
    assert len(backup_files) == 1
    # assert backup file is named <name>.softsave_yymmdd-HHMMSS
    for file in backup_files:
        assert re.match(
            r"^" + DEVICE_NAME + r"\.softsav_[0-9]{6}-[0-9]{6}$", file.name
        )


def test_autosave_key_names(tmp_path):
    builder.aOut("DEFAULTNAME", autosave=True)
    builder.SetDeviceName(DEVICE_NAME)
    builder.aOut("DEFAULTNAMEAFTERPREFIXSET", autosave=True)
    builder.aOut("RENAMEME", autosave=True, autosave_name="CUSTOMNAME")
    autosave.configure(tmp_path, DEVICE_NAME)
    autosaver = autosave.Autosave()
    autosaver._save()
    with open(tmp_path / f"{DEVICE_NAME}.softsav", "r") as f:
        saved = yaml.full_load(f)
    assert "DEFAULTNAME" in saved
    assert "DEFAULTNAMEAFTERPREFIXSET" in saved
    assert "CUSTOMNAME" in saved
