import atexit
import sys
import threading
import traceback
from datetime import datetime
from os import rename
from pathlib import Path
from shutil import copy2

import numpy
import yaml

SAV_SUFFIX = "softsav"
SAVB_SUFFIX = "softsavB"
DEFAULT_SAVE_PERIOD = 30.0


def _ndarray_representer(dumper, array):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", array.tolist(), flow_style=True
    )


yaml.add_representer(numpy.ndarray, _ndarray_representer, Dumper=yaml.Dumper)


def configure(
    directory,
    name,
    save_period=DEFAULT_SAVE_PERIOD,
    timestamped_backups=True,
    enabled=True,
):
    """This should be called before initialising the IOC. Configures the
    autosave thread for periodic backing up of PV values.

    Args:
        directory: string or Path giving directory path where autosave backup
            files are saved and loaded.
        name: string name of the root used for naming backup files. This
            is usually the same as the device name.
        save_period: time in seconds between backups. Backups are only performed
            if PV values have changed.
        timestamped_backups: boolean which determines if backups of existing
            autosave files are timestamped on IOC restart. True by default, if
            False then backups get overwritten on each IOC restart.
        enabled: boolean which enables or disables autosave, set to True by
            default, or False if configure not called.
    """
    directory_path = Path(directory)
    if not directory_path.is_dir():
        raise FileNotFoundError(
            f"{directory} is not a valid autosave directory"
        )
    AutosaveConfig.directory = directory_path
    AutosaveConfig.timestamped_backups = timestamped_backups
    AutosaveConfig.save_period = save_period
    AutosaveConfig.enabled = enabled
    AutosaveConfig.device_name = name


class AutosaveConfig:
    directory = None
    device_name = None
    timestamped_backups = True
    save_period = DEFAULT_SAVE_PERIOD
    enabled = False


def start_autosave_thread():
    worker = threading.Thread(
        target=Autosave._loop,
    )
    worker.start()
    atexit.register(_shutdown_autosave_thread, worker)


def _shutdown_autosave_thread(worker):
    Autosave._stop()
    worker.join()


def add_pv_to_autosave(pv, name, kargs):
    """Configures a PV for autosave

    Args:
        pv: a PV object inheriting ProcessDeviceSupportCore
        name: the key by which the PV value is saved to and loaded from a
            backup. This is typically the same as the PV name.
        kargs: a dictionary containing the optional keys "autosave", a boolean
            used to add the VAL field to autosave backups, and
            "autosave_fields", a list of string field names to save to the
            backup file.
    """

    autosaver = Autosave()
    # instantiate to get thread local class variables via instance
    if autosaver._in_cm:
        # non-None autosave argument to PV takes priority over context manager
        autosave_karg = kargs.pop("autosave", None)
        save_val = (
            autosave_karg
            if autosave_karg is not None
            else autosaver._cm_save_val
        )
        save_fields = (
            kargs.pop("autosave_fields", []) + autosaver._cm_save_fields
        )
    else:
        save_val = kargs.pop("autosave", False)
        save_fields = kargs.pop("autosave_fields", [])
    if save_val:
        Autosave._pvs[name] = _AutosavePV(pv)
    if save_fields:
        for field in save_fields:
            Autosave._pvs[f"{name}.{field}"] = _AutosavePV(pv, field)


def load_autosave():
    Autosave._load()


class _AutosavePV:
    def __init__(self, pv, field=None):
        if not field or field == "VAL":
            self.get = pv.get
            self.set = pv.set
        else:
            self.get = lambda: pv.get_field(field)
            self.set = lambda val: setattr(pv, field, val)


def _get_current_sav_path():
    return (
        AutosaveConfig.directory / f"{AutosaveConfig.device_name}.{SAV_SUFFIX}"
    )


def _get_tmp_sav_path():
    return (
        AutosaveConfig.directory / f"{AutosaveConfig.device_name}.{SAVB_SUFFIX}"
    )


def _get_timestamped_backup_sav_path(timestamp):
    sav_path = _get_current_sav_path()
    return sav_path.parent / (
        sav_path.name + timestamp.strftime("_%y%m%d-%H%M%S")
    )


def _get_backup_sav_path():
    sav_path = _get_current_sav_path()
    return sav_path.parent / (sav_path.name + ".bu")


class Autosave(threading.local):
    _instance = None
    _singleton_lock = threading.Lock()
    _pvs = {}
    _last_saved_state = {}
    _last_saved_time = datetime.now()
    _stop_event = threading.Event()
    _loop_started = False
    _cm_save_val = False
    _cm_save_fields = []
    _in_cm = False

    def __new__(cls, autosave=None, autosave_fields=None):
        # Make Autosave a Singleton class so that we have thread local
        # class variables when accessed via instance
        if cls._instance is None:
            with cls._singleton_lock:
                # Another thread could have created the instance
                # before we acquired the lock. So check that the
                # instance is still nonexistent.
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        if autosave is not None:
            cls._instance._cm_save_val = autosave
        if autosave_fields is not None:
            cls._instance._cm_save_fields = autosave_fields or []
        return cls._instance

    def __enter__(self):
        self._in_cm = True

    def __exit__(self, A, B, C):
        self._in_cm = False
        self._cm_save_val = False
        self._cm_save_fields = []
        self._instance = None

    @classmethod
    def __backup_sav_file(cls):
        if (
            not AutosaveConfig.directory
            or not AutosaveConfig.directory.is_dir()
        ):
            print(
                f"Could not back up autosave as {AutosaveConfig.directory} is"
                " not a valid directory",
                file=sys.stderr,
            )
            return
        sav_path = _get_current_sav_path()
        if AutosaveConfig.timestamped_backups:
            backup_path = _get_timestamped_backup_sav_path(cls._last_saved_time)
        else:
            backup_path = _get_backup_sav_path()
        if sav_path.is_file():
            copy2(sav_path, backup_path)
        else:
            print(
                f"Could not back up autosave, {sav_path} is not a file",
                file=sys.stderr,
            )

    @classmethod
    def __get_state(cls):
        state = {}
        for pv_field, pv in cls._pvs.items():
            try:
                state[pv_field] = pv.get()
            except Exception:
                print(f"Exception getting {pv_field}", file=sys.stderr)
                traceback.print_exc()
        return state

    @classmethod
    def __set_pvs_from_saved_state(cls):
        for pv_field, value in cls._last_saved_state.items():
            try:
                pv = cls._pvs[pv_field]
                pv.set(value)
            except Exception:
                print(
                    f"Exception setting {pv_field} to {value}",
                    file=sys.stderr,
                )
                traceback.print_exc()

    @classmethod
    def __state_changed(cls, state):
        return cls._last_saved_state.keys() != state.keys() or any(
            # checks equality for builtins and numpy arrays
            not numpy.array_equal(state[key], cls._last_saved_state[key])
            for key in state
        )

    @classmethod
    def _save(cls):
        state = cls.__get_state()
        if cls.__state_changed(state):
            sav_path = _get_current_sav_path()
            tmp_path = _get_tmp_sav_path()
            # write to temporary file first then use atomic os.rename
            # to safely update stored state
            with open(tmp_path, "w") as backup:
                yaml.dump(state, backup, indent=4)
            rename(tmp_path, sav_path)
            cls._last_saved_state = state
            cls._last_saved_time = datetime.now()

    @classmethod
    def _load(cls):
        if not AutosaveConfig.enabled or not cls._pvs:
            return
        if not AutosaveConfig.device_name:
            raise RuntimeError(
                "Device name is not known to autosave thread, "
                "call autosave.configure() with keyword argument name"
            )
        if not AutosaveConfig.directory:
            raise RuntimeError(
                "Autosave directory is not known, call "
                "autosave.configure() with keyword argument directory"
            )
        if not AutosaveConfig.directory.is_dir():
            raise FileNotFoundError(
                f"{AutosaveConfig.directory} is not a valid autosave directory"
            )
        cls.__backup_sav_file()
        sav_path = _get_current_sav_path()
        if not sav_path or not sav_path.is_file():
            print(
                f"Could not load autosave values from file {sav_path}",
                file=sys.stderr,
            )
            return
        with open(sav_path, "r") as f:
            cls._last_saved_state = yaml.full_load(f)
        cls.__set_pvs_from_saved_state()

    @classmethod
    def _stop(cls):
        cls._stop_event.set()

    @classmethod
    def _loop(cls):
        if not AutosaveConfig.enabled or not cls._pvs or cls._loop_started:
            return
        cls._loop_started = True
        while True:
            try:
                cls._stop_event.wait(timeout=AutosaveConfig.save_period)
                cls._save()
                if cls._stop_event.is_set():  # Stop requested
                    return
            except Exception:
                traceback.print_exc()
