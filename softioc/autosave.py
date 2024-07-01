import json
from pathlib import Path
from typing import Dict, List, Optional
from softioc.pythonSoftIoc import RecordWrapper
from datetime import datetime
import shutil

SAV_SUFFIX = "softsav"
SAVB_SUFFIX = "softsavB"


class Autosave:
    def __init__(
        self,
        device_name: str,
        directory: str,
        pvs: List[RecordWrapper],
        save_period: float = 30.0,
        enabled: bool = True,
        backup_on_restart: bool = True
    ):
        self._device: str = device_name
        self._directory: Path = Path(directory)  # cast string to Path
        self._last_saved_time = datetime.now()
        if not self._directory.is_dir():
            raise RuntimeError(f"{directory} is not a valid autosave directory")
        if backup_on_restart:
            self.backup_sav_file()
        self._enabled = enabled
        self._save_period = save_period
        self._pvs = {pv.name: pv for pv in pvs}
        self._state: Dict[str, RecordWrapper] = {}
        self._last_saved_state = {}

    def _change_directory(self, directory: str):
        dir_path = Path(directory)
        if dir_path.is_dir():
            self._directory = dir_path
        else:
            raise ValueError(f"{directory} is not a valid autosave directory")

    def backup_sav_file(self):
        sav_path = self._get_current_sav_path()
        if sav_path.is_file():
            shutil.copy2(sav_path, self._get_timestamped_backup_sav_path())

    def add_pv(self, pv: RecordWrapper):
        self._pvs[pv.name] = pv

    def remove_pv(self, pv: RecordWrapper):
        self._pvs.pop(pv.name, None)

    def _get_state_from_device(self):
        for name, pv in self._pvs.items():
            self._state[name] = pv.get()

    def _get_timestamped_backup_sav_path(self) -> Path:
        sav_path = self._get_current_sav_path()
        return sav_path.parent / (
            sav_path.name + self._last_saved_time.strftime("_%y%m%d-%H%M%S")
        )

    def _get_backup_save_path(self) -> Path:
        return self._directory / f"{self._device}.{SAVB_SUFFIX}"

    def _get_current_sav_path(self) -> Path:
        return self._directory / f"{self._device}.{SAV_SUFFIX}"

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
        if not self._enabled:
            print("Not saving to file as autosave adapter disabled")
            return
        timenow = datetime.now()
        self._get_state_from_device()
        if (
            (timenow - self._last_saved_time).total_seconds() > self._save_period
            and self._state != self._last_saved_state  # only save if changed
        ):
            self._save()

    def load(self, path: Optional[str] = None):
        if not self._enabled:
            print("Not loading from file as autosave adapter disabled")
            return
        sav_path = path or self._get_current_sav_path()
        with open(sav_path, "r") as f:
            state = json.load(f)
        for name, value in state.items():
            pv = self._pvs.get(name, None)
            if not pv:
                print(f"{name} is not a valid autosaved PV")
                continue
            pv.set(value)
        self._get_state_from_device()
