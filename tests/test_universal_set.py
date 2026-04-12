"""Tests for universal set(): verify set() publishes immediately
regardless of SCAN setting.

Tests use ``sim_universal_set_ioc.py`` running in a subprocess.
The test harness communicates commands over a multiprocessing
connection to trigger set() calls on the Python side, while
monitoring values via Channel Access from the test process.
"""

import asyncio
import time
import pytest

from multiprocessing.connection import Listener

from aioca import caget, camonitor

from conftest import (
    ADDRESS, TIMEOUT,
    select_and_recv, aioca_cleanup,
)


# ---------------------------------------------------------------- #
# Helpers                                                          #
# ---------------------------------------------------------------- #

def _pv(prefix, suffix):
    return f"{prefix}:{suffix}"


async def _set_and_verify(conn, prefix, rec_name, value, timeout=5.0):
    """Tell the IOC to set() a value, then caget to confirm publication."""
    conn.send(("set", rec_name, value))
    reply = conn.recv()
    assert reply == "OK", f"set command failed: {reply}"
    await asyncio.sleep(0.5)
    return await caget(_pv(prefix, rec_name), timeout=timeout)


async def _change_scan(conn, rec_name, scan_value):
    """Tell the IOC to change SCAN via dbpf."""
    conn.send(("scan", rec_name, scan_value))
    reply = conn.recv()
    assert reply == "OK", f"scan command failed: {reply}"
    await asyncio.sleep(0.3)


# ================================================================ #
#  1.  BASELINE: set() works with default I/O Intr                  #
# ================================================================ #

class TestSetWithIOIntr:
    """Baseline: set() works with the default I/O Intr SCAN."""

    @pytest.mark.asyncio
    async def test_ai_set_io_intr(self, universal_set_ioc):
        """aIn.set() publishes immediately with SCAN='I/O Intr'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                got = await _set_and_verify(conn, p, "AI", 42.5)
                assert got == pytest.approx(42.5, abs=0.01)
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_ao_set_io_intr(self, universal_set_ioc):
        """aOut.set() publishes immediately with SCAN='I/O Intr'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                got = await _set_and_verify(conn, p, "AO", 3.14)
                assert got == pytest.approx(3.14, abs=0.01)
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_longin_set_io_intr(self, universal_set_ioc):
        """longIn.set() publishes immediately with SCAN='I/O Intr'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                got = await _set_and_verify(conn, p, "LONGIN", 99)
                assert got == 99
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  2.  set() with SCAN = Passive                                    #
# ================================================================ #

class TestSetWithPassive:
    """set() must publish immediately even when SCAN='Passive'."""

    @pytest.mark.asyncio
    async def test_ai_set_passive(self, universal_set_ioc):
        """aIn.set() works after switching to SCAN='Passive'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "Passive")
                got = await _set_and_verify(conn, p, "AI", 77.7)
                assert got == pytest.approx(77.7, abs=0.01), \
                    f"set() with Passive SCAN: expected 77.7, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_ao_set_passive(self, universal_set_ioc):
        """aOut.set() works after switching to SCAN='Passive'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AO", "Passive")
                got = await _set_and_verify(conn, p, "AO", 2.718)
                assert got == pytest.approx(2.718, abs=0.01), \
                    f"set() with Passive SCAN: expected 2.718, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_longin_set_passive(self, universal_set_ioc):
        """longIn.set() works after switching to SCAN='Passive'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "LONGIN", "Passive")
                got = await _set_and_verify(conn, p, "LONGIN", 123)
                assert got == 123, \
                    f"set() with Passive SCAN: expected 123, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_bo_set_passive(self, universal_set_ioc):
        """boolOut.set() works after switching to SCAN='Passive'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "BO", "Passive")
                got = await _set_and_verify(conn, p, "BO", 1)
                assert got == 1, \
                    f"set() with Passive SCAN: expected 1, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  3.  set() with periodic SCAN settings                            #
# ================================================================ #

class TestSetWithPeriodicScan:
    """set() must publish immediately even with periodic SCAN."""

    @pytest.mark.asyncio
    async def test_ai_set_1_second(self, universal_set_ioc):
        """aIn.set() publishes immediately, doesn't wait for scan period."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "1 second")
                got = await _set_and_verify(conn, p, "AI", 55.5)
                assert got == pytest.approx(55.5, abs=0.01), \
                    f"set() with 1 second SCAN: expected 55.5, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_ai_set_5_second(self, universal_set_ioc):
        """aIn.set() publishes immediately with SCAN='5 second'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "5 second")
                got = await _set_and_verify(conn, p, "AI", 88.8)
                assert got == pytest.approx(88.8, abs=0.01), \
                    f"set() with 5 second SCAN: expected 88.8, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_ai_set_10_second(self, universal_set_ioc):
        """aIn.set() publishes immediately with SCAN='10 second'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "10 second")
                got = await _set_and_verify(conn, p, "AI", 33.3)
                assert got == pytest.approx(33.3, abs=0.01), \
                    f"set() with 10 second SCAN: expected 33.3, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_ao_set_2_second(self, universal_set_ioc):
        """aOut.set() publishes immediately with SCAN='2 second'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AO", "2 second")
                got = await _set_and_verify(conn, p, "AO", 6.28)
                assert got == pytest.approx(6.28, abs=0.01), \
                    f"set() with 2 second SCAN: expected 6.28, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  4.  set() with SCAN = Event                                      #
# ================================================================ #

class TestSetWithEventScan:
    """set() must publish immediately with SCAN='Event'."""

    @pytest.mark.asyncio
    async def test_ai_set_event(self, universal_set_ioc):
        """aIn.set() publishes immediately with SCAN='Event'."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "Event")
                got = await _set_and_verify(conn, p, "AI", 11.1)
                assert got == pytest.approx(11.1, abs=0.01), \
                    f"set() with Event SCAN: expected 11.1, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  5.  SCAN transitions: switch back and forth                      #
# ================================================================ #

class TestScanTransitions:
    """set() continues to work when switching between SCAN values."""

    @pytest.mark.asyncio
    async def test_io_intr_to_passive_and_back(self, universal_set_ioc):
        """set() works across I/O Intr -> Passive -> I/O Intr."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                got = await _set_and_verify(conn, p, "AI", 1.0)
                assert got == pytest.approx(1.0, abs=0.01)

                await _change_scan(conn, "AI", "Passive")
                got = await _set_and_verify(conn, p, "AI", 2.0)
                assert got == pytest.approx(2.0, abs=0.01)

                await _change_scan(conn, "AI", "I/O Intr")
                got = await _set_and_verify(conn, p, "AI", 3.0)
                assert got == pytest.approx(3.0, abs=0.01)
            finally:
                aioca_cleanup()
                conn.send("D")

    @pytest.mark.asyncio
    async def test_io_intr_to_periodic_to_passive(self, universal_set_ioc):
        """set() works across I/O Intr -> 1 second -> Passive."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "1 second")
                got = await _set_and_verify(conn, p, "AI", 10.0)
                assert got == pytest.approx(10.0, abs=0.01)

                await _change_scan(conn, "AI", "Passive")
                got = await _set_and_verify(conn, p, "AI", 20.0)
                assert got == pytest.approx(20.0, abs=0.01)
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  6.  Multiple rapid set() calls with non-I/O-Intr SCAN           #
# ================================================================ #

class TestRapidSets:
    """Multiple rapid set() calls should all be processed."""

    @pytest.mark.asyncio
    async def test_rapid_sets_passive(self, universal_set_ioc):
        """Last of several rapid set() calls wins on Passive record."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            try:
                await _change_scan(conn, "AI", "Passive")

                for val in [10.0, 20.0, 30.0]:
                    conn.send(("set", "AI", val))
                    reply = conn.recv()
                    assert reply == "OK"

                await asyncio.sleep(1.0)

                got = await caget(_pv(p, "AI"), timeout=TIMEOUT)
                assert got == pytest.approx(30.0, abs=0.01), \
                    f"Expected final value 30.0, got {got}"
            finally:
                aioca_cleanup()
                conn.send("D")


# ================================================================ #
#  7.  Monitor receives updates from set() on non-I/O-Intr          #
# ================================================================ #

class TestMonitorUpdates:
    """CA monitors see updates from set() regardless of SCAN."""

    @pytest.mark.asyncio
    async def test_monitor_sees_set_on_passive(self, universal_set_ioc):
        """camonitor receives update when set() fires on a Passive record."""
        p = universal_set_ioc.pv_prefix
        with Listener(ADDRESS) as listener, listener.accept() as conn:
            select_and_recv(conn, "R")
            received = []

            try:
                pv = _pv(p, "AI")
                sub = camonitor(pv, received.append)

                await asyncio.sleep(0.5)  # let initial monitor connect

                await _change_scan(conn, "AI", "Passive")

                conn.send(("set", "AI", 99.9))
                reply = conn.recv()
                assert reply == "OK"

                deadline = time.time() + 5.0
                while time.time() < deadline:
                    if any(abs(float(v) - 99.9) < 0.1 for v in received):
                        break
                    await asyncio.sleep(0.1)

                sub.close()

                assert any(abs(float(v) - 99.9) < 0.1 for v in received), \
                    f"Monitor never received 99.9, got: {received}"
            finally:
                aioca_cleanup()
                conn.send("D")
