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

from .device_core import LookupRecordList

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
    enabled=True
):
    """This should be called before initialising the IOC. Configures the
    autosave thread for periodic backing up of PV values.

    Args:
        directory: string or Path giving directory path where autosave backup
            files are saved and loaded.
        name: string name of the root used for naming backup files, this
            is usually the same as the device name.
        save_period: time in seconds between backups. Backups are only performed
            if PV values have changed.
        timestamped_backups: boolean which determines if backups of existing
            autosave files are timestamped on IOC restart. True by default, if
            False then backups get overwritten on each IOC restart.
        enabled: boolean which enables or disables autosave, set to True by
            default, or False if configure not called.
    """
    Autosave.directory = Path(directory)
    Autosave.timestamped_backups = timestamped_backups
    Autosave.save_period = save_period
    Autosave.enabled = enabled
    Autosave.device_name = name


def start_autosave_thread():
    autosaver = Autosave()
    worker = threading.Thread(
        target=autosaver.loop,
    )
    worker.daemon = True
    worker.start()
    atexit.register(_shutdown_autosave_thread, autosaver, worker)


def _shutdown_autosave_thread(autosaver, worker):
    autosaver.stop()
    worker.join()


def add_pv_to_autosave(pv, name, save_val, save_fields):
    """Configures a PV for autosave

    Args:
        pv: a PV object inheriting ProcessDeviceSupportCore
        name: the name of the PV which is used to generate the key
            by which the PV value is saved to and loaded from a backup,
            this is typically the same as the PV name.
        save_val: a boolean that tracks whether to save the VAL field
            in an autosave backup
        save_fields: a list of string names of fields associated with the pv
            to be saved to and loaded from a backup
    """
    if save_val:
        Autosave._pvs[name] = _AutosavePV(pv)
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


class Autosave:
    _pvs = {}
    _last_saved_state = {}
    _last_saved_time = datetime.now()
    _stop_event = threading.Event()
    save_period = DEFAULT_SAVE_PERIOD
    device_name = None
    directory = None
    enabled = False
    timestamped_backups = True
    _loop_started = False

    def __init__(self, autosave=True, autosave_fields=None):
        # for use as a context manager
        self._save_val = autosave
        self._save_fields = autosave_fields or []

    def __enter__(self):
        if self._save_val or self._save_fields:
            self._records_before_cm = dict(LookupRecordList())
        else:
            self._records_before_cm = {}

    def __exit__(self, A, B, C):
        if self._save_val or self._save_fields:
            for key, pv in LookupRecordList():
                try:
                    if key not in self._records_before_cm:
                        add_pv_to_autosave(
                            pv, key, self._save_val, self._save_fields)
                except Exception:
                    traceback.print_exc()
        self._save_val = False
        self._save_fields = []
        self._records_before_cm = None


    @classmethod
    def __backup_sav_file(cls):
        if not cls.directory and cls.directory.is_dir():
            print(
                f"Could not back up autosave as {cls.directory} is"
                " not a valid directory",
                file=sys.stderr,
            )
            return
        sav_path = cls.__get_current_sav_path()
        if cls.timestamped_backups:
            backup_path = cls.__get_timestamped_backup_sav_path()
        else:
            backup_path = cls.__get_backup_sav_path()
        if sav_path.is_file():
            copy2(sav_path, backup_path)
        else:
            print(
                f"Could not back up autosave, {sav_path} is not a file",
                file=sys.stderr,
            )

    @classmethod
    def __get_timestamped_backup_sav_path(cls):
        sav_path = cls.__get_current_sav_path()
        return sav_path.parent / (
            sav_path.name + cls._last_saved_time.strftime("_%y%m%d-%H%M%S")
        )

    @classmethod
    def __get_backup_sav_path(cls):
        sav_path = cls.__get_current_sav_path()
        return sav_path.parent / (sav_path.name + ".bu")

    @classmethod
    def __get_tmp_sav_path(cls):
        return cls.directory / f"{cls.device_name}.{SAVB_SUFFIX}"

    @classmethod
    def __get_current_sav_path(cls):
        return cls.directory / f"{cls.device_name}.{SAV_SUFFIX}"

    def __get_state(self):
        state = {}
        for pv_field, pv in self._pvs.items():
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

    def __state_changed(self, state):
        return self._last_saved_state.keys() != state.keys() or any(
            # checks equality for builtins and numpy arrays
            not numpy.array_equal(state[key], self._last_saved_state[key])
            for key in state
        )

    def _save(self):
        state = self.__get_state()
        if self.__state_changed(state):
            sav_path = self.__get_current_sav_path()
            tmp_path = self.__get_tmp_sav_path()
            # write to temporary file first then use atomic os.rename
            # to safely update stored state
            with open(tmp_path, "w") as backup:
                yaml.dump(state, backup, indent=4)
            rename(tmp_path, sav_path)
            self._last_saved_state = state
            self._last_saved_time = datetime.now()

    @classmethod
    def _load(cls):
        if not cls.enabled or not cls._pvs:
            return
        if not cls.device_name:
            raise RuntimeError(
                "Device name is not known to autosave thread, "
                "call autosave.configure() with keyword argument name"
            )
        if not cls.directory:
            raise RuntimeError(
                "Autosave directory is not known, call "
                "autosave.configure() with keyword argument directory"
            )
        if not cls.directory.is_dir():
            raise FileNotFoundError(
                f"{cls.directory} is not a valid autosave directory"
            )
        cls.__backup_sav_file()
        sav_path = cls.__get_current_sav_path()
        if not sav_path or not sav_path.is_file():
            print(
                f"Could not load autosave values from file {sav_path}",
                file=sys.stderr,
            )
            return
        with open(sav_path, "r") as f:
            cls._last_saved_state = yaml.full_load(f)
        cls.__set_pvs_from_saved_state()

    def stop(self):
        self._stop_event.set()

    def loop(self):
        if not self.enabled or not self._pvs or self._loop_started:
            return
        self._loop_started = True
        while True:
            try:
                self._stop_event.wait(timeout=self.save_period)
                self._save()
                if self._stop_event.is_set():  # Stop requested
                    return
            except Exception:
                traceback.print_exc()
