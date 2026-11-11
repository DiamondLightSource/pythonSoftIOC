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


def _parse_autosave_fields(fields):
    if not fields:
        return []
    elif fields is True:
        return ["VAL"]
    elif isinstance(fields, list):
        return fields
    elif isinstance(fields, str):
        return [fields]
    else:
        raise ValueError(f"Could not parse autosave fields argument: {fields}")


def add_pv_to_autosave(pv, name, fields):
    """Configures a PV for autosave

    Args:
        pv: a PV object inheriting ProcessDeviceSupportCore
        name: the key by which the PV value is saved to and loaded from a
            backup. This is typically the same as the PV name.
        fields: used to determine which fields of a PV are tracked by autosave.
            The allowed options are a single string such as "VAL" or "EGU",
            a list of strings such as ["VAL", "EGU"], a boolean True which
            evaluates to ["VAL"] or False to track no fields. If the PV is
            created inside an Autosave context manager, the fields passed to the
            context manager are also tracked by autosave.
    """
    if fields is False:
        # if autosave=False explicitly set, override context manager
        return
    fields = set(_parse_autosave_fields(fields))
    # instantiate context to get thread local class variables via instance
    context = _AutosaveContext()
    if context._in_cm:  # _fields should always be a list if in context manager
        fields.update(context._fields)
    for field in fields:
        field_name = name if field == "VAL" else f"{name}.{field}"
        Autosave._pvs[field_name] = _AutosavePV(pv, field)


def load_autosave():
    Autosave._load()


class _AutosavePV:
    def __init__(self, pv, field):
        if field == "VAL":
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


class _AutosaveContext(threading.local):
    _instance = None
    _lock = threading.Lock()
    _fields = None
    _in_cm = False

    def __new__(cls, fields=None):
        if cls._instance is None:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        if cls._instance._in_cm and fields is not None:
            cls._instance._fields = fields or []
        return cls._instance

    def reset(self):
        self._fields = None
        self._in_cm = False


class Autosave:
    _pvs = {}
    _last_saved_state = {}
    _last_saved_time = datetime.now()
    _stop_event = threading.Event()
    _loop_started = False

    def __init__(self, fields=True):
        """
        When called as a context manager, any PVs created in the context have
        the fields provided by the fields argument added to autosave backups.

        Args:
            fields: a list of string field names to be periodically saved to a
            backup file, which are loaded from on IOC restart.
            The allowed options are a single string such as "VAL" or "EGU",
            a list of strings such as ["VAL", "EGU"], a boolean True which
            evaluates to ["VAL"] or False to track no additional fields.
            If the autosave keyword is already specified in a PV's
            initialisation, the list of fields to track are combined.
        """
        context = _AutosaveContext()
        if context._in_cm:
            raise RuntimeError(
                "Can not instantiate Autosave when already in context manager"
            )
        fields = _parse_autosave_fields(fields)
        context._fields = fields

    def __enter__(self):
        context = _AutosaveContext()
        context._in_cm = True

    def __exit__(self, A, B, C):
        context = _AutosaveContext()
        context.reset()

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
