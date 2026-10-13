# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Cocotb tests for the clock divider (src/io/clkdiv.sv).
# Run with `make -f Makefile.clkdiv`. clkdiv is the toplevel here, so we drive
# b, c, q, clk and rst_n directly.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge
from reference_models.clkdiv import ClkdivRef

CLK_PERIOD_NS = 40  # 25 MHz

# Settings from docs/modules/io/clkdiv.md. c is negative, so the 8-bit port
# holds the two's complement form (-18 -> 238, -1 -> 255).
B_115200, C_115200 = 104, 238
B_230400, C_230400 = 43, 238


async def start_clkdiv(dut, b: int, c: int) -> None:
    # Start the clock, hold reset with these settings, then let it run.
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.rst_n.value = 0
    dut.b.value = b
    dut.c.value = c
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1


async def check_against_ref(dut, ref: ClkdivRef, cycles: int, label: str = "") -> None:
    # Step the reference and the DUT together and check q matches every cycle.
    # We read in ReadOnly so we see the values after the edge. Then q is the
    # state after i edges, which is what ref.q is after i ticks, so compare
    # first and tick after.
    for i in range(cycles):
        await ReadOnly()
        ref_output = ref.q
        dut_output = int(dut.q.value)
        assert ref_output == dut_output, (
            f"Mismatch at cycle {i}{label}: ref={ref_output}, dut={dut_output}"
        )
        ref.tick()
        await RisingEdge(dut.clk)


async def measure_ratio(dut, cycles: int) -> float:
    # Count output toggles over `cycles`. Each toggle is half a period, so
    # toggles / 2 is the number of full periods.
    toggles = 0
    prev_q = int(dut.q.value)
    for _ in range(cycles):
        curr_q = int(dut.q.value)
        if curr_q != prev_q:
            toggles += 1
        prev_q = curr_q
        await ClockCycles(dut.clk, 1)

    return (toggles / 2) / cycles


@cocotb.test()
async def test_clkdiv_reset(dut):
    # q should be 0 while reset is held.
    dut._log.info("clkdiv reset")

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.rst_n.value = 0
    dut.b.value = B_115200
    dut.c.value = C_115200
    await ClockCycles(dut.clk, 5)

    await ReadOnly()
    assert dut.q.value == 0, f"Expected q=0 after reset, got {dut.q.value}"
    dut._log.info("✓ Output is 0 after reset")

    await RisingEdge(dut.clk)  # can't write inside ReadOnly
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


