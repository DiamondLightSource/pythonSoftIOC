"""
CLS extension: field-write monitor.

Bridges the low-level C ``asTrapWrite`` hook to the per-record Python
callbacks registered via :meth:`DeviceSupportCore.on_field_change`.

After ``iocInit()``, call :func:`install_field_monitor` once.  From that
point on every CA/PVA-originated write to any record field triggers
:func:`_dispatch_field_write`, which resolves the record, and invokes the
matching callbacks (exact field match **plus** any ``"*"`` wildcard
callbacks).

.. note::

   IOC-shell writes (``dbpf``) and internal ``record.set()`` calls bypass
   ``asTrapWrite`` and will **not** fire callbacks.
"""

import logging

from .device_core import LookupRecord
from . import imports

__all__ = ['install_field_monitor']

_log = logging.getLogger(__name__)


def _parse_channel_name(channel_name):
    """Split a channel name into ``(record_name, field_name)``.

    Returns:
        tuple: ``("RECNAME", "FIELD")`` or ``("RECNAME", "VAL")`` when
        the channel was addressed without a dot suffix.
    """
    if "." in channel_name:
        return channel_name.rsplit(".", 1)
    return channel_name, "VAL"


def _dispatch_field_write(channel_name, value_str):
    """Called from C for every CA/PVA field write (post-write).

    Resolves the target record via :func:`LookupRecord` and invokes
    every callback registered for the written field **and** any ``"*"``
    wildcard callbacks.
    """
    rec_name, field = _parse_channel_name(channel_name)

    try:
        record = LookupRecord(rec_name)
    except KeyError:
        return  # Not one of our soft-IOC records — nothing to do.

    for cb in record._get_field_callbacks(field):
        try:
            cb(rec_name, field, value_str)
        except Exception:
            _log.exception(
                "field-change callback error for %s.%s", rec_name, field
            )


def install_field_monitor(auto_reset_scan=False):
    """Register :func:`_dispatch_field_write` with the C extension.

    Must be called **after** ``iocInit()`` and after the access-security
    file (containing the ``TRAPWRITE`` rule) has been loaded — both of
    which are handled automatically by :func:`softioc.iocInit`.

    Args:
        auto_reset_scan: If True, the C layer resets SCAN back to
            "I/O Intr" after every non-Passive SCAN write, eliminating
            periodic-scan contention.  Default False.
    """
    imports.register_field_write_listener(
        _dispatch_field_write, auto_reset_scan=auto_reset_scan)
