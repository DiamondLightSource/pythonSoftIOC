import yaml
import shutil
import threading
from datetime import datetime
from pathlib import Path
from numpy import ndarray
from softioc.device_core import LookupRecordList
import sys
import atexit

SAV_SUFFIX = "softsav"
SAVB_SUFFIX = "softsavB"


def _ndarray_representer(dumper, array):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", array.tolist(), flow_style=True
    )


def configure(directory=None, save_period=None, enabled=True, device=None):
    '''This should be called before initialising the IOC. Configures the
    autosave thread for periodic backing up of PV values.

    Args:
        directory: string or Path giving directory path where autosave files
            should be saved and loaded, must be supplied before iocInit if
            autosave is required.
        save_period: time in seconds between backups. Backups are only performed
            if PV values have changed.
        enabled: boolean which enables or disables autosave, set to True by
            default, or False if configure not called.
        device: string name of the device prefix used for naming autosave files,
            automatically supplied by builder if not explicitly provided.
    '''
    # if already set, do not overwrite save_period or directory
    Autosave.save_period = save_period or Autosave.save_period
    Autosave.enabled = enabled
    if directory is not None:
        Autosave.directory = Path(directory)
    if device is None:
        if Autosave.device_name is None:
            from .builder import GetRecordNames
            Autosave.device_name = GetRecordNames().prefix[0]
    else:
        Autosave.device_name = device


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


class Autosave:
    _pvs = {}
    _last_saved_state = {}
    _stop_event = threading.Event()
    save_period = 30.0
    device_name = None
    directory = None
    enabled = False
    backup_on_restart = True

    def __init__(self):
        if not self.enabled:
            return
        yaml.add_representer(
            ndarray, _ndarray_representer, Dumper=yaml.Dumper
        )
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
        if self.backup_on_restart:
            self._backup_sav_file()
        self._pvs = {name: pv for name, pv in LookupRecordList() if pv.autosave}

    def _backup_sav_file(self):
        sav_path = self._get_current_sav_path()
        if sav_path.is_file():
            shutil.copy2(sav_path, self._get_timestamped_backup_sav_path())
        else:
            sys.stderr.write(
                f"Could not back up autosave, {sav_path} is not a file"
            )

    def _get_timestamped_backup_sav_path(self):
        sav_path = self._get_current_sav_path()
        return sav_path.parent / (
            sav_path.name + self._last_saved_time.strftime("_%y%m%d-%H%M%S")
        )

    def _get_backup_save_path(self):
        return self.directory / f"{self.device_name}.{SAVB_SUFFIX}"

    def _get_current_sav_path(self):
        return self.directory / f"{self.device_name}.{SAV_SUFFIX}"

    def _save(self):
        try:
            state = {name: pv.get() for name, pv in self._pvs.items()}
            if state != self._last_saved_state:
                for path in [
                    self._get_current_sav_path(),
                    self._get_backup_save_path()
                ]:
                    with open(path, "w") as f:
                        yaml.dump(state, f, indent=4)
                self._last_saved_state = state
                self._last_saved_time = datetime.now()
        except Exception as e:
            sys.stderr.write(f"Could not save state to file: {e}")

    def _load(self, path=None):
        if not self.enabled:
            sys.stdout.write(
                "Not loading from file as autosave adapter disabled"
            )
            return
        sav_path = path or self._get_current_sav_path()
        if not sav_path or not sav_path.is_file():
            sys.stderr.write(
                f"Could not load autosave values from file {sav_path}"
            )
            return
        with open(sav_path, "r") as f:
            self._last_saved_state = yaml.full_load(f)
        for name, value in self._last_saved_state.items():
            try:
                pv = self._pvs.get(name)
                pv.set(value)
            except Exception as e:
                sys.stderr.write(f"Exception setting {name} to {value}: {e}")

    def stop(self):
        self._stop_event.set()

    def loop(self):
        if not self.enabled or not self._pvs:
            return
        # wait until iocInit has been called
        # TODO: put in a timeout here otherwise this may get silently stuck...
        while True:
            if all(hasattr(pv, "_record") for pv in self._pvs.values()):
                break
        self._load()  # load at startup if enabled
        while True:
            try:
                self._stop_event.wait(timeout=self.save_period)
                if self._stop_event.is_set():  # Stop requested
                    return
                else:  # No stop requested, we should save and continue
                    self._save()
            except Exception as e:
                sys.stderr.write(f"Exception in autosave loop: {e}")
