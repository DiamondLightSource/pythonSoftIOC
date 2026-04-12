"""Behavioral tests: PV field writes vs pythonSoftIOC processing.

Goal
----
Verify that writing to standard EPICS record fields (SCAN, DISA,
HIHI, DRVH, etc.) via Channel Access does **not** break pSIOC's
device-support layer, and document which behaviors are handled
by the EPICS libraries vs which are pSIOC-specific.

Each test covers one "concern" and is self-contained.
All tests use the subprocess IOC
``sim_field_behavior_ioc.py``.
"""

import asyncio
import time
import pytest

from multiprocessing.connection import Listener

from aioca import caget, caput, FORMAT_CTRL, FORMAT_TIME

from conftest import (
    ADDRESS, TIMEOUT,
    select_and_recv, aioca_cleanup,
)


# ---------------------------------------------------------------- #
# Helpers                                                          #
# ---------------------------------------------------------------- #

def _pv(prefix, suffix):
    return f"{prefix}:{suffix}"


async def _wait_for(prefix, pv_suffix, expected, timeout=TIMEOUT):
    """Poll a PV until it reaches *expected* or timeout."""
    pv = _pv(prefix, pv_suffix)
    deadline = time.time() + timeout
    while time.time() < deadline:
        val = await caget(pv, timeout=TIMEOUT)
        if val >= expected:
            return val
        await asyncio.sleep(0.1)
    return await caget(pv, timeout=TIMEOUT)


# ================================================================ #
#  1.  DRIVE LIMITS  (DRVH / DRVL)                                 #
# ================================================================ #

class TestDriveLimits:
    """EPICS ao record support clamps VAL to [DRVL, DRVH]."""

    @pytest.mark.asyncio
    async def test_initial_drvh_clamp(self, field_behavior_ioc):
        """caput value > DRVH is clamped to DRVH."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO"), 100.0,
                            timeout=TIMEOUT, wait=True)
                val = await caget(_pv(p, "AO"), timeout=TIMEOUT)
                assert val == pytest.approx(50.0), (
                    f"Expected clamped to DRVH=50, got {val}"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_initial_drvl_clamp(self, field_behavior_ioc):
        """caput value < DRVL is clamped to DRVL."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO"), -100.0,
                            timeout=TIMEOUT, wait=True)
                val = await caget(_pv(p, "AO"), timeout=TIMEOUT)
                assert val == pytest.approx(-50.0), (
                    f"Expected clamped to DRVL=-50, got {val}"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_change_drvh_via_ca(self, field_behavior_ioc):
        """Changing DRVH via CA updates the effective clamp."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO.DRVH"), 80.0, timeout=TIMEOUT)
                await asyncio.sleep(0.2)
                await caput(_pv(p, "AO"), 75.0,
                            timeout=TIMEOUT, wait=True)
                val = await caget(_pv(p, "AO"), timeout=TIMEOUT)
                assert val == pytest.approx(75.0), (
                    f"DRVH=80: caput 75 should pass, got {val}"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_on_update_with_clamped(self, field_behavior_ioc):
        """on_update callback fires even when clamped."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO"), 999.0,
                            timeout=TIMEOUT, wait=True)
                cnt = await _wait_for(
                    p, "AO-UPDATE-CNT", cnt0 + 1,
                )
                assert cnt >= cnt0 + 1
                val = await caget(_pv(p, "AO"), timeout=TIMEOUT)
                assert val <= 50.0
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  2.  ALARM LIMITS  (HIHI / HIGH / LOW / LOLO)                    #
# ================================================================ #

class TestAlarmLimits:
    """EPICS record support evaluates alarm thresholds."""

    @pytest.mark.asyncio
    async def test_hihi_major(self, field_behavior_ioc):
        """Value > HIHI -> MAJOR alarm."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                # DRVH is 50, HIHI is 90; raise DRVH first
                await caput(_pv(p, "AO.DRVH"), 100.0, timeout=TIMEOUT)
                await asyncio.sleep(0.1)
                await caput(_pv(p, "AO"), 95.0,
                            timeout=TIMEOUT, wait=True)
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_TIME, timeout=TIMEOUT)
                assert r.severity == 2, (
                    f"Expected MAJOR(2) for 95>HIHI=90, "
                    f"got {r.severity}"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_high_minor(self, field_behavior_ioc):
        """Value > HIGH but < HIHI -> MINOR alarm."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO.DRVH"), 100.0, timeout=TIMEOUT)
                await asyncio.sleep(0.1)
                await caput(_pv(p, "AO"), 75.0,
                            timeout=TIMEOUT, wait=True)
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_TIME, timeout=TIMEOUT)
                assert r.severity == 1, (
                    f"Expected MINOR(1) for 75>HIGH=70, "
                    f"got {r.severity}"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_change_hihi_clears_alarm(
        self, field_behavior_ioc
    ):
        """Raising HIHI above current value clears alarm."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO.DRVH"), 100.0, timeout=TIMEOUT)
                await caput(_pv(p, "AO.HIGH"), 100.0, timeout=TIMEOUT)
                await asyncio.sleep(0.1)
                await caput(_pv(p, "AO"), 95.0,
                            timeout=TIMEOUT, wait=True)
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_TIME, timeout=TIMEOUT)
                assert r.severity == 2  # MAJOR

                await caput(_pv(p, "AO.HIHI"), 100.0, timeout=TIMEOUT)
                await asyncio.sleep(0.1)
                # Re-write to re-process
                await caput(_pv(p, "AO"), 95.0,
                            timeout=TIMEOUT, wait=True)
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_TIME, timeout=TIMEOUT)
                assert r.severity == 0, (
                    "HIHI=100: val=95 should be NO_ALARM"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_on_update_under_alarm(self, field_behavior_ioc):
        """on_update fires even when record is in alarm."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO"), 45.0,
                            timeout=TIMEOUT, wait=True)
                cnt = await _wait_for(
                    p, "AO-UPDATE-CNT", cnt0 + 1,
                )
                assert cnt >= cnt0 + 1
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  3.  SCAN FIELD                                                   #
# ================================================================ #

class TestScanField:
    """SCAN controls when EPICS processes the record.
    pSIOC defaults to I/O Intr."""

    @pytest.mark.asyncio
    async def test_default_scan(self, field_behavior_ioc):
        """pSIOC sets SCAN='I/O Intr' for input records.
        Output records (aOut) default to 'Passive'."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                # aOut defaults to Passive (not I/O Intr)
                ao_scan = await caget(
                    _pv(p, "AO.SCAN"),
                    datatype=str, timeout=TIMEOUT,
                )
                assert "Passive" in str(ao_scan)
                # aIn defaults to I/O Intr
                ai_scan = await caget(
                    _pv(p, "AI.SCAN"),
                    datatype=str, timeout=TIMEOUT,
                )
                assert "I/O Intr" in str(ai_scan)
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_periodic_scan(self, field_behavior_ioc):
        """SCAN='1 second' causes periodic on_update calls."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO"), 10.0,
                            timeout=TIMEOUT, wait=True)
                await asyncio.sleep(0.3)
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO.SCAN"), "1 second",
                            datatype=str, timeout=TIMEOUT)
                await asyncio.sleep(2.5)
                cnt1 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                # Restore
                await caput(_pv(p, "AO.SCAN"), "I/O Intr",
                            datatype=str, timeout=TIMEOUT)
                assert cnt1 >= cnt0 + 2, (
                    f"Expected >=2 extra calls, "
                    f"got {cnt1 - cnt0}"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_passive_no_auto(self, field_behavior_ioc):
        """AO defaults to Passive.  Explicit caput still
        triggers on_update via dbProcess."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                # AO is already Passive by default
                scan = await caget(_pv(p, "AO.SCAN"),
                                   datatype=str, timeout=TIMEOUT)
                assert "Passive" in str(scan)
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                # caput to VAL triggers dbPutField -> dbProcess
                await caput(_pv(p, "AO"), 5.0,
                            timeout=TIMEOUT, wait=True)
                cnt = await _wait_for(
                    p, "AO-UPDATE-CNT", cnt0 + 1,
                )
                assert cnt >= cnt0 + 1, (
                    "Explicit caput triggers on_update"
                )
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  4.  DISABLE (DISA / DISV)                                        #
# ================================================================ #

class TestDisable:
    """DISA==DISV disables record processing."""

    @pytest.mark.asyncio
    async def test_disa_suppresses_on_update(
        self, field_behavior_ioc
    ):
        """With DISA=1 (==DISV), on_update does NOT fire."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO"), 1.0,
                            timeout=TIMEOUT, wait=True)
                await asyncio.sleep(0.3)
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO.DISA"), 1, timeout=TIMEOUT)
                await asyncio.sleep(0.2)
                await caput(_pv(p, "AO"), 2.0,
                            timeout=TIMEOUT, wait=True)
                await asyncio.sleep(0.5)
                cnt1 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO.DISA"), 0, timeout=TIMEOUT)
                assert cnt1 == cnt0, (
                    "on_update should NOT fire when disabled"
                )
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_disa_re_enable(self, field_behavior_ioc):
        """After clearing DISA, processing resumes."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO.DISA"), 1, timeout=TIMEOUT)
                await asyncio.sleep(0.2)
                await caput(_pv(p, "AO.DISA"), 0, timeout=TIMEOUT)
                await asyncio.sleep(0.2)
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO"), 3.0,
                            timeout=TIMEOUT, wait=True)
                cnt = await _wait_for(
                    p, "AO-UPDATE-CNT", cnt0 + 1,
                )
                assert cnt >= cnt0 + 1
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_field_change_fires_when_disabled(
        self, field_behavior_ioc
    ):
        """on_field_change fires even when record is disabled
        (asTrapWrite fires before record-support checks)."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO.DISA"), 1, timeout=TIMEOUT)
                await asyncio.sleep(0.2)
                await caput(_pv(p, "AO.HIHI"), 42.0, timeout=TIMEOUT)
                await asyncio.sleep(0.3)
                f = await caget(_pv(p, "LAST-FIELD"),
                                datatype=str, timeout=TIMEOUT)
                await caput(_pv(p, "AO.DISA"), 0, timeout=TIMEOUT)
                assert f == "HIHI", (
                    "field_change should fire when disabled"
                )
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  5.  DISPLAY RANGE & EGU  (LOPR / HOPR / EGU)                    #
# ================================================================ #

class TestDisplayRange:
    """LOPR, HOPR, EGU are metadata fields visible in
    ctrl-format caget."""

    @pytest.mark.asyncio
    async def test_initial_egu(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_CTRL, timeout=TIMEOUT)
                egu = r.units
                if isinstance(egu, bytes):
                    egu = egu.decode()
                assert egu == "V"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_change_egu(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "AO.EGU"), "mA", timeout=TIMEOUT)
                await asyncio.sleep(0.2)
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_CTRL, timeout=TIMEOUT)
                egu = r.units
                if isinstance(egu, bytes):
                    egu = egu.decode()
                assert egu == "mA"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_change_lopr_hopr(self, field_behavior_ioc):
        """For ao records, ctrl limits are driven by DRVL/DRVH.
        LOPR/HOPR are display hints; CA ctrl limit returns
        max(DRVL,LOPR) and min(DRVH,HOPR) respectively."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                # Initial DRVL=-50, DRVH=50, LOPR=-100, HOPR=100
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_CTRL, timeout=TIMEOUT)
                # ctrl limits reflect DRVL/DRVH for ao
                assert r.lower_ctrl_limit == \
                    pytest.approx(-50.0)
                assert r.upper_ctrl_limit == \
                    pytest.approx(50.0)
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  6.  PRECISION (PREC)                                             #
# ================================================================ #

class TestPrecision:
    """PREC controls display precision for float records."""

    @pytest.mark.asyncio
    async def test_initial_prec(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_CTRL, timeout=TIMEOUT)
                assert r.precision == 3
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_change_prec(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(
                    _pv(p, "AO.PREC"), 5,
                    timeout=TIMEOUT,
                )
                await asyncio.sleep(0.2)
                r = await caget(_pv(p, "AO"),
                                format=FORMAT_CTRL, timeout=TIMEOUT)
                assert r.precision == 5
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  7.  INPUT RECORD: metadata reads                                 #
# ================================================================ #

class TestInputRecord:
    """Input records (ai) are driven by Python set().
    External clients can read values and metadata."""

    @pytest.mark.asyncio
    async def test_ai_initial_value(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                val = await caget(_pv(p, "AI"), timeout=TIMEOUT)
                assert val == pytest.approx(0.0)
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_ai_alarm_limits(self, field_behavior_ioc):
        """Alarm limits reported in ctrl struct."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                r = await caget(_pv(p, "AI"),
                                format=FORMAT_CTRL, timeout=TIMEOUT)
                assert r.upper_alarm_limit == \
                    pytest.approx(90.0)
                assert r.upper_warning_limit == \
                    pytest.approx(70.0)
                assert r.lower_warning_limit == \
                    pytest.approx(-70.0)
                assert r.lower_alarm_limit == \
                    pytest.approx(-90.0)
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  8.  FIELD-CHANGE vs ON_UPDATE interaction                        #
# ================================================================ #

class TestFieldChangeVsOnUpdate:
    """on_field_change (CLS) and on_update coexist."""

    @pytest.mark.asyncio
    async def test_val_fires_both(self, field_behavior_ioc):
        """caput VAL fires both on_update and
        on_field_change('*')."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "AO"), 10.0,
                            timeout=TIMEOUT, wait=True)
                await asyncio.sleep(0.3)
                cnt1 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                f = await caget(_pv(p, "LAST-FIELD"),
                                datatype=str, timeout=TIMEOUT)
                assert cnt1 >= cnt0 + 1, (
                    "on_update should fire"
                )
                assert f == "VAL"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_non_val_no_on_update(
        self, field_behavior_ioc
    ):
        """caput to non-VAL field fires on_field_change
        but NOT on_update."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                cnt0 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(
                    _pv(p, "AO.EGU"), "Hz",
                    timeout=TIMEOUT,
                )
                await asyncio.sleep(0.3)
                cnt1 = await caget(
                    _pv(p, "AO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                f = await caget(_pv(p, "LAST-FIELD"),
                                datatype=str, timeout=TIMEOUT)
                assert cnt1 == cnt0, (
                    "on_update should NOT fire for EGU"
                )
                assert f == "EGU"
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  9.  BOOLEAN OUTPUT                                               #
# ================================================================ #

class TestBooleanOutput:
    """Boolean records use the same field-write path."""

    @pytest.mark.asyncio
    async def test_bo_on_update(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                cnt0 = await caget(
                    _pv(p, "BO-UPDATE-CNT"), timeout=TIMEOUT,
                )
                await caput(_pv(p, "BO"), 1,
                            timeout=TIMEOUT, wait=True)
                cnt = await _wait_for(
                    p, "BO-UPDATE-CNT", cnt0 + 1,
                )
                assert cnt >= cnt0 + 1
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_bo_toggle(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(_pv(p, "BO"), 1,
                            timeout=TIMEOUT, wait=True)
                v = await caget(_pv(p, "BO"), timeout=TIMEOUT)
                assert v == 1
                await caput(_pv(p, "BO"), 0,
                            timeout=TIMEOUT, wait=True)
                v = await caget(_pv(p, "BO"), timeout=TIMEOUT)
                assert v == 0
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  10. DESC FIELD (40-char metadata)                                #
# ================================================================ #

class TestDescField:
    """DESC is a 40-character string metadata field."""

    @pytest.mark.asyncio
    async def test_set_desc(self, field_behavior_ioc):
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await caput(
                    _pv(p, "AO.DESC"), "Test desc",
                    timeout=TIMEOUT,
                )
                await asyncio.sleep(0.2)
                r = await caget(_pv(p, "AO.DESC"),
                                datatype=str, timeout=TIMEOUT)
                assert r == "Test desc"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_desc_truncation(self, field_behavior_ioc):
        """DESC is limited to 40 chars.  CA client rejects
        strings longer than MAX_STRING_SIZE (40) at the
        client level -- no server round-trip needed."""
        p = field_behavior_ioc.pv_prefix
        with Listener(ADDRESS) as listener, \
                listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                # Exactly 39 chars should work
                await caput(
                    _pv(p, "AO.DESC"), "A" * 39,
                    timeout=TIMEOUT,
                )
                await asyncio.sleep(0.2)
                r = await caget(_pv(p, "AO.DESC"),
                                datatype=str, timeout=TIMEOUT)
                assert len(r) == 39
            finally:
                aioca_cleanup()
                conn.send("D")
