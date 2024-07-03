import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import shutil
from softioc.device_core import LookupRecordList
import time
import threading

SAV_SUFFIX = "softsav"
SAVB_SUFFIX = "softsavB"

def configure(device=None, directory=None, save_period=None, poll_period=None):
    Autosave.poll_period = poll_period or Autosave.poll_period
    Autosave.save_period = save_period or Autosave.save_period
    if device is None and Autosave.device_name is None:
        from .builder import GetRecordNames
        Autosave.device_name = GetRecordNames().prefix[0]
    else:
        Autosave.device_name = device
    if directory is None and Autosave.directory is None:
        raise RuntimeError("Autosave directory is not known, "
                           "call autosave.configure() with directory keyword argument")
    else:
        Autosave.directory = Path(directory)

class Autosave:
    _instance = None
    poll_period = 1.0
    save_period = 30.0
    device_name = None
    directory = None
    enabled = True
    backup_on_restart = True

    def __init__(
        self,
    ):
        if not self.directory:
            raise RuntimeError("Autosave directory is not known, "
                           "call autosave.configure() with directory keyword argument")
        if not self.device_name:
            raise RuntimeError("Device name is not known to autosave thread, "
                "call autosave.configure() with device keyword argument")
        self._last_saved_time = datetime.now()
        if not self.directory.is_dir():
            raise RuntimeError(f"{directory} is not a valid autosave directory")
        if self.backup_on_restart:
            self.backup_sav_file()
        self.get_autosave_pvs()
        self._state = {}
        self._last_saved_state = {}
        self._started = False
        if self.enabled:
            self.load()  # load at startup if enabled

    def get_autosave_pvs(self):
        self._pvs = {name: pv for name, pv in LookupRecordList() if pv.autosave}

    def _change_directory(self, directory: str):
        dir_path = Path(directory)
        if dir_path.is_dir():
            self.directory = dir_path
        else:
            raise ValueError(f"{directory} is not a valid autosave directory")

    def backup_sav_file(self):
        sav_path = self._get_current_sav_path()
        if sav_path.is_file():
            shutil.copy2(sav_path, self._get_timestamped_backup_sav_path())

    def add_pv(self, pv):
        pv.autosave = True
        self._pvs[pv.name] = pv

    def remove_pv(self, pv):
        pv.autosave = False
        self._pvs.pop(pv.name, None)

    def _get_state_from_device(self):
        for name, pv in self._pvs.items():
            self._state[name] = pv.get()

    def _get_timestamped_backup_sav_path(self):
        sav_path = self._get_current_sav_path()
        return sav_path.parent / (
            sav_path.name + self._last_saved_time.strftime("_%y%m%d-%H%M%S")
        )

    def _get_backup_save_path(self):
        return self.directory / f"{self.device_name}.{SAVB_SUFFIX}"

    def _get_current_sav_path(self):
        return self.directory / f"{self.device_name}.{SAV_SUFFIX}"

    def _update_last_saved(self):
        self._last_saved_state = self._state.copy()
        self._last_saved_time = datetime.now()

    def _save(self):
        try:
            for path in [self._get_current_sav_path(), self._get_backup_save_path()]:
                with open(path, "w") as f:
                    json.dump(self._state, f, indent=4)
            self._update_last_saved()
        except Exception as e:
            print(f"Could not save state to file: {e}")

    def save(self):
        if not self.enabled:
            print("Not saving to file as autosave adapter disabled")
            return
        timenow = datetime.now()
        self._get_state_from_device()
        if (
            (timenow - self._last_saved_time).total_seconds() > self.save_period
            and self._state != self._last_saved_state  # only save if changed
        ):
            self._save()

    def load(self, path = None):
        if not self.enabled:
            print("Not loading from file as autosave adapter disabled")
            return
        sav_path = path or self._get_current_sav_path()
        if not sav_path or not sav_path.is_file():
            print(f"Could not load autosave values from file {sav_path}")
            return
        with open(sav_path, "r") as f:
            state = json.load(f)
        for name, value in state.items():
            pv = self._pvs.get(name, None)
            if not pv:
                print(f"{name} is not a valid autosaved PV")
                continue
            pv.set(value)
        self._get_state_from_device()

    def loop(self):
        if not self._pvs:
            return  # end thread if no PVs to save
        while True:
            time.sleep(self.poll_period)
            self.save()
