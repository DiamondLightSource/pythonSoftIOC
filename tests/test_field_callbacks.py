"""Tests for the CLS ``on_field_change`` extension.

The IOC runs in a subprocess (``sim_field_callbacks_ioc.py``) so that it has
its own EPICS database and Channel Access / PV Access servers — exactly the
same architecture used by the other pythonSoftIOC tests.

What is tested
--------------
* CA write to a non-VAL control field (SCAN, DISA) fires the
  registered callback.
* CA write to VAL fires the VAL callback.
* CA write to an alarm field (HIHI) fires its callback.
  Alarm fields are ``DBF_DOUBLE``; this confirms no special
  casing vs other types.
* CA write to a string metadata field (DESC) fires its callback.
  DESC is ``DBF_STRING``; this confirms the
  ``dbGetField(DBR_STRING)`` path works for fields whose native
  type is already a string.
* PVA write to VAL fires the VAL callback.
* PVA write to a non-VAL field (SCAN) fires the callback.
  This is the only protocol difference that needs explicit verification —
  pvxs uses a different field-addressing model for subfields.
* Multiple writes to the same field accumulate correctly in the counter.
* A callback on one field does not increment another field's counter.
* A wildcard ``"*"`` callback fires for every field write.
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
# CA tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_field_callbacks_ca(field_callbacks_ioc):
    """CA puts to SCAN, DISA and VAL each fire the correct callback."""
    from aioca import caget, caput

    pre = field_callbacks_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            # -- SCAN field --
            await caput(pre + ":AO.SCAN", "1 second", wait=True)
            await asyncio.sleep(0.5)
            assert await caget(pre + ":SCAN-CB-CNT") == 1

            # -- DISA field --
            await caput(pre + ":AO.DISA", 1, wait=True)
            await asyncio.sleep(0.5)
            assert await caget(pre + ":DISA-CB-CNT") == 1

            # -- VAL field via CA --
            await caput(pre + ":AO", 42.0, wait=True)
            await asyncio.sleep(0.5)
            assert await caget(pre + ":VAL-CB-CNT") == 1

            # -- Multiple SCAN writes accumulate --
            await caput(pre + ":AO.SCAN", "2 second", wait=True)
            await caput(pre + ":AO.SCAN", ".5 second", wait=True)
            await asyncio.sleep(0.5)
            assert await caget(pre + ":SCAN-CB-CNT") == 3

            # -- Isolation: SCAN writes do not affect DISA counter --
            assert await caget(pre + ":DISA-CB-CNT") == 1

            # -- Wildcard: every write (3 SCAN + 1 DISA + 1 VAL = 5) --
            assert await caget(pre + ":ANY-CB-CNT") == 5
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# PVA test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_field_callbacks_pva(field_callbacks_ioc):
    """A PVA put to VAL fires the VAL callback and the wildcard callback."""
    from aioca import caget
    from p4p.client.asyncio import Context

    pre = field_callbacks_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            with Context("pva") as ctx:
                await asyncio.wait_for(
                    ctx.put(pre + ":AO", 99.0), timeout=TIMEOUT
                )

            await asyncio.sleep(0.5)
            assert await caget(pre + ":VAL-CB-CNT") == 1
            assert await caget(pre + ":ANY-CB-CNT") == 1  # wildcard
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


# ---------------------------------------------------------------------------
# Field-type coverage tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_field_callbacks_alarm_field(field_callbacks_ioc):
    """Alarm field (HIHI, DBF_DOUBLE) uses the same callback path as VAL.

    This is the key "no special casing" assertion: alarm limits go through
    asTrapWrite identically to any other writeable field.
    """
    from aioca import caget, caput

    pre = field_callbacks_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO.HIHI", 95.0, wait=True)
            await asyncio.sleep(0.5)
            assert await caget(pre + ":HIHI-CB-CNT") == 1
            assert await caget(pre + ":ANY-CB-CNT") == 1   # wildcard also fires
            # Other counters must remain zero — no cross-field leakage.
            assert await caget(pre + ":VAL-CB-CNT") == 0
            assert await caget(pre + ":SCAN-CB-CNT") == 0
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


@pytest.mark.asyncio
async def test_field_callbacks_string_field(field_callbacks_ioc):
    """String metadata field (DESC, DBF_STRING) is captured correctly.

    The C hook reads every value through ``dbGetField(DBR_STRING)``.  For
    fields whose native type is already a string (like DESC) the value must
    round-trip without corruption.
    """
    from aioca import caget, caput

    pre = field_callbacks_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            await caput(pre + ":AO.DESC", "test label", wait=True)
            await asyncio.sleep(0.5)
            assert await caget(pre + ":DESC-CB-CNT") == 1
            assert await caget(pre + ":ANY-CB-CNT") == 1
            # Other counters must remain zero.
            assert await caget(pre + ":VAL-CB-CNT") == 0
            assert await caget(pre + ":HIHI-CB-CNT") == 0
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")


@pytest.mark.asyncio
async def test_field_callbacks_pva_non_val(field_callbacks_ioc):
    """A PVA put to a non-VAL field (SCAN) fires the callback.

    pvxs addresses subfields differently from VAL writes.  This test
    confirms that the asTrapWrite hook fires regardless of which field
    a PVA client targets.
    """
    from aioca import caget
    from p4p.client.asyncio import Context

    pre = field_callbacks_ioc.pv_prefix

    with Listener(ADDRESS) as listener, listener.accept() as conn:
        select_and_recv(conn, "R")

        try:
            with Context("pva") as ctx:
                await asyncio.wait_for(
                    ctx.put(pre + ":AO.SCAN", "1 second"), timeout=TIMEOUT
                )

            await asyncio.sleep(0.5)
            assert await caget(pre + ":SCAN-CB-CNT") == 1
            assert await caget(pre + ":ANY-CB-CNT") == 1   # wildcard
            assert await caget(pre + ":VAL-CB-CNT") == 0   # not triggered
        finally:
            aioca_cleanup()
            conn.send("D")
            select_and_recv(conn, "D")
