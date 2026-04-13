"""Tests for the CLS callback refinements.

Uses ``sim_callback_refinements_ioc.py`` which exercises:

* **Multi-field subscription** —
  ``on_field_change(["DRVH", "DRVL", "HIHI"], cb)``
  registers a single callback for multiple fields.
* **on_update coexistence** — ``on_update`` and ``on_field_change("VAL", cb)``
  both fire on a VAL write without interfering with each other.
* **Wildcard fires for all writes** — ``on_field_change("*", cb)``
  sees every field write.
* **auto_reset_scan** — When enabled via ``iocInit(auto_reset_scan=True)``,
  an external SCAN write (e.g. "1 second") is forwarded to the Python
  callback but the SCAN field is immediately reset to "I/O Intr".
  Passive writes are exempt from the reset.
"""

import asyncio

import pytest

from multiprocessing.connection import Listener

from conftest import (
    ADDRESS,
    select_and_recv,
    aioca_cleanup,
    TIMEOUT,
)


# ---------------------------------------------------------------------------
# Multi-field subscription tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_field_subscription(callback_refinements_ioc):
    """on_field_change(["DRVH","DRVL","HIHI"], cb) fires for each field."""
    from aioca import caget, caput

    pre = callback_refinements_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            # Each write to a different listed field should fire _multi_cb
            await caput(pre + ":AO.DRVH", 100.0, wait=True)
            await asyncio.sleep(0.3)
            assert await caget(pre + ":MULTI-CB-CNT") == 1

            await caput(pre + ":AO.DRVL", -100.0, wait=True)
            await asyncio.sleep(0.3)
            assert await caget(pre + ":MULTI-CB-CNT") == 2

            await caput(pre + ":AO.HIHI", 99.0, wait=True)
            await asyncio.sleep(0.3)
            assert await caget(pre + ":MULTI-CB-CNT") == 3
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# on_update coexistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_on_update_coexistence(callback_refinements_ioc):
    """on_update and on_field_change("VAL") both fire on a VAL write."""
    from aioca import caget, caput

    pre = callback_refinements_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO", 42.0, wait=True)
            await asyncio.sleep(0.3)

            # on_update should have fired
            assert await caget(pre + ":ON-UPDATE-CNT") == 1
            # on_field_change("VAL") should also have fired
            assert await caget(pre + ":VAL-CB-CNT") == 1
            # Wildcard must also fire
            assert await caget(pre + ":WILDCARD-CNT") == 1
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# Wildcard accumulation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wildcard_accumulation(callback_refinements_ioc):
    """Wildcard counter accumulates across different field writes."""
    from aioca import caget, caput

    pre = callback_refinements_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            # Three distinct field writes
            await caput(pre + ":AO.DRVH", 100.0, wait=True)
            await caput(pre + ":AO.DRVL", -100.0, wait=True)
            await caput(pre + ":AO", 5.0, wait=True)
            await asyncio.sleep(0.5)

            # Wildcard fires for each: DRVH, DRVL, VAL = 3
            assert await caget(pre + ":WILDCARD-CNT") == 3
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# Multi-field isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multi_field_isolation(callback_refinements_ioc):
    """Multi-field callback only fires for subscribed fields, not others."""
    from aioca import caget, caput

    pre = callback_refinements_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            # Writing to VAL should NOT increment MULTI-CB-CNT
            await caput(pre + ":AO", 5.0, wait=True)
            await asyncio.sleep(0.3)
            assert await caget(pre + ":MULTI-CB-CNT") == 0
            # But VAL-CB-CNT should fire
            assert await caget(pre + ":VAL-CB-CNT") == 1
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# auto_reset_scan: disabled (default)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scan_no_auto_reset(callback_refinements_ioc):
    """Without auto_reset_scan, SCAN stays at whatever the client wrote."""
    from aioca import caget, caput

    pre = callback_refinements_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO.SCAN", "1 second", wait=True)
            await asyncio.sleep(0.5)

            # Callback should fire
            assert await caget(pre + ":SCAN-CB-CNT") == 1
            # SCAN stays at "1 second" (no reset)
            scan_val = await caget(pre + ":AO.SCAN", datatype=str)
            assert scan_val == "1 second"
        finally:
            # Reset SCAN to Passive before leaving
            await caput(pre + ":AO.SCAN", "Passive", wait=True)
            await asyncio.sleep(0.3)
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# auto_reset_scan: enabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scan_auto_reset(auto_reset_scan_ioc):
    """With auto_reset_scan, SCAN is reset to I/O Intr after callback fires."""
    from aioca import caget, caput

    pre = auto_reset_scan_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO.SCAN", "1 second", wait=True)
            await asyncio.sleep(0.5)

            # Callback should have seen "1 second"
            assert await caget(pre + ":SCAN-CB-CNT") == 1
            last_val = await caget(pre + ":LAST-SCAN-VAL")
            assert last_val == "1 second"

            # But SCAN should now read "I/O Intr" (auto-reset)
            scan_val = await caget(pre + ":AO.SCAN", datatype=str)
            assert scan_val == "I/O Intr"
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


@pytest.mark.asyncio
async def test_scan_auto_reset_passive_exempt(auto_reset_scan_ioc):
    """Passive SCAN writes are exempt from auto_reset_scan."""
    from aioca import caget, caput

    pre = auto_reset_scan_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO.SCAN", "Passive", wait=True)
            await asyncio.sleep(0.5)

            # SCAN stays at Passive (not reset to I/O Intr)
            scan_val = await caget(pre + ":AO.SCAN", datatype=str)
            assert scan_val == "Passive"
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


@pytest.mark.asyncio
async def test_scan_auto_reset_multiple(auto_reset_scan_ioc):
    """Multiple SCAN writes each fire the callback and get reset."""
    from aioca import caget, caput

    pre = auto_reset_scan_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO.SCAN", "1 second", wait=True)
            await asyncio.sleep(0.5)
            await caput(pre + ":AO.SCAN", "2 second", wait=True)
            await asyncio.sleep(0.5)

            # Both writes should have fired the callback
            assert await caget(pre + ":SCAN-CB-CNT") == 2
            # The last value seen should be "2 second"
            last_val = await caget(pre + ":LAST-SCAN-VAL")
            assert last_val == "2 second"
            # SCAN should be reset after the second write
            scan_val = await caget(pre + ":AO.SCAN", datatype=str)
            assert scan_val == "I/O Intr"
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# Callback de-registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remove_field_callback(callback_refinements_ioc):
    """remove_field_callback stops the callback from firing."""
    from aioca import caget, caput

    pre = callback_refinements_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            # Phase 1: _dereg_cb is registered — DRVH write fires it.
            await caput(pre + ":AO.DRVH", 100.0, wait=True)
            await asyncio.sleep(0.3)
            assert await caget(pre + ":DEREG-CB-CNT") == 1
            # _multi_cb also fires (DRVH is in the list).
            assert await caget(pre + ":MULTI-CB-CNT") == 1

            # Phase 2: ask subprocess to de-register _dereg_cb.
            conn.send("P")
            select_and_recv(conn, "K")

            # Phase 3: another DRVH write — _dereg_cb should NOT fire.
            await caput(pre + ":AO.DRVH", 200.0, wait=True)
            await asyncio.sleep(0.3)
            assert await caget(pre + ":DEREG-CB-CNT") == 1  # unchanged
            # _multi_cb still fires (it was not removed).
            assert await caget(pre + ":MULTI-CB-CNT") == 2
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")
