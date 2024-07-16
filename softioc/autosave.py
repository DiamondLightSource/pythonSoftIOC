import atexit
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

import numpy
import yaml
from numpy import ndarray
from os import rename
from shutil import copy2

SAV_SUFFIX = "softsav"
SAVB_SUFFIX = "softsavB"


def _ndarray_representer(dumper, array):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", array.tolist(), flow_style=True
    )


def configure(directory, name, save_period=None, backup=True, enabled=True):
    """This should be called before initialising the IOC. Configures the
    autosave thread for periodic backing up of PV values.

    Args:
        directory: string or Path giving directory path where autosave backup
            files are saved and loaded.
        nane: string name of the root used for naming backup files, this
            could be the same as the device prefix.
        save_period: time in seconds between backups. Backups are only performed
            if PV values have changed.
        backup: creates a backup of the loaded autosave file on load,
            timestamped with the time of backup.
        enabled: boolean which enables or disables autosave, set to True by
            default, or False if configure not called.
    """
    Autosave.directory = Path(directory)
    Autosave.backup_on_load = backup
    Autosave.save_period = save_period or Autosave.save_period
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


def add_pv_to_autosave(pv, name, val, fields):
    if val:
        Autosave._pvs[name] = _AutosavePV(pv)
    for field in fields:
        Autosave._pvs[f"{name}.{field}"] = _AutosavePV(pv, field)


def load():
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
    save_period = 30.0
    device_name = None
    directory = None
    enabled = False
    backup_on_load = True

    def __init__(self):
        if not self.enabled:
            return
        yaml.add_representer(ndarray, _ndarray_representer, Dumper=yaml.Dumper)
        if not self.device_name:
            raise RuntimeError(
                "Device name is not known to autosave thread, "
                "call autosave.configure() with keyword argument device"
            )
        if not self.directory:
            raise RuntimeError(
                "Autosave directory is not known, call "
                "autosave.configure() with keyword argument "
                "directory"
            )
        if not self.directory.is_dir():
            raise FileNotFoundError(
                f"{self.directory} is not a valid autosave directory"
            )
        self._last_saved_time = datetime.now()

    @classmethod
    def _backup_sav_file(cls):
        sav_path = cls._get_current_sav_path()
        if sav_path.is_file():
            copy2(sav_path, cls._get_timestamped_backup_sav_path())
        else:
            sys.stderr.write(
                f"Could not back up autosave, {sav_path} is not a file\n"
            )
            sys.stderr.flush()

    @classmethod
    def _get_timestamped_backup_sav_path(cls):
        sav_path = cls._get_current_sav_path()
        return sav_path.parent / (
            sav_path.name + cls._last_saved_time.strftime("_%y%m%d-%H%M%S")
        )

    @classmethod
    def _get_backup_sav_path(cls):
        return cls.directory / f"{cls.device_name}.{SAVB_SUFFIX}"

    @classmethod
    def _get_current_sav_path(cls):
        return cls.directory / f"{cls.device_name}.{SAV_SUFFIX}"

    def _get_state(self):
        state = {}
        for pv_field, pv in self._pvs.items():
            try:
                state[pv_field] = pv.get()
            except Exception as e:
                sys.stderr.write(f"Exception getting {pv_field}: {e}\n")
        sys.stderr.flush()
        return state

    @classmethod
    def _set_pvs_from_saved_state(cls):
        for pv_field, value in cls._last_saved_state.items():
            try:
                pv = cls._pvs[pv_field]
                pv.set(value)
            except Exception as e:
                sys.stderr.write(
                    f"Exception setting {pv_field} to {value}: {e}\n"
                )
        sys.stderr.flush()

    def _state_changed(self, state):
        return self._last_saved_state.keys() != state.keys() or any(
            # checks equality for builtins and numpy arrays
            not numpy.array_equal(state[key], self._last_saved_state[key])
            for key in state
        )

    def _save(self):
        state = self._get_state()
        if self._state_changed(state):
            sav_path = self._get_current_sav_path()
            backup_path = self._get_backup_sav_path()
            # write to backup file first then use atomic os.rename
            # to safely update stored state
            with open(backup_path, "w") as backup:
                yaml.dump(state, backup, indent=4)
            rename(backup_path, sav_path)
            self._last_saved_state = state
            self._last_saved_time = datetime.now()

    @classmethod
    def _load(cls, path=None):
        if cls.backup_on_load:
            cls._backup_sav_file()
        if not cls.enabled or not cls._pvs:
            return
        sav_path = path or cls._get_current_sav_path()
        if not sav_path or not sav_path.is_file():
            sys.stderr.write(
                f"Could not load autosave values from file {sav_path}\n"
            )
            sys.stderr.flush()
            return
        with open(sav_path, "r") as f:
            cls._last_saved_state = yaml.full_load(f)
        cls._set_pvs_from_saved_state()

    def stop(self):
        self._stop_event.set()

    def loop(self):
        if not self.enabled or not self._pvs:
            return
        while True:
            try:
                self._stop_event.wait(timeout=self.save_period)
                self._save()
                if self._stop_event.is_set():  # Stop requested
                    return
            except Exception:
                traceback.print_exc()
