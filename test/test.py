# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from reference_models.clkdiv import ClkdivRef


@cocotb.test()
async def test_project(dut):
    """Smoke test: the wired-up top elaborates, resets, and runs.

    The modules below the top are still stubs, so this only checks the pins
    that the top drives itself. Add checks here as modules are implemented.
    """
    dut._log.info("Start")

    # Set the clock period to 40 ns (25 MHz)
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Reset, with the UART receive line (ui_in[3]) idle high
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0b0000_1000
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Run")
    await ClockCycles(dut.clk, 100)

    # The bidirectional pins are all inputs
    assert dut.uio_oe.value == 0


# Clock divider tests
@cocotb.test()
async def test_clkdiv_reset(dut):
    """clkdiv should go to 0 on reset."""
    dut._log.info("clkdiv reset")

    clock = Clock(dut.clk, 40, units="ns")  # 25 MHz
    cocotb.start_soon(clock.start())

    # Apply reset
    dut.rst_n.value = 0
    dut.b.value = 104
    dut.c.value = 238  # -18 as unsigned 8-bit
    await ClockCycles(dut.clk, 5)

    # After reset, output should be 0
    assert dut.q.value == 0, f"Expected q=0 after reset, got {dut.q.value}"
    dut._log.info("✓ Output is 0 after reset")

    # Release reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


@cocotb.test()
async def test_clkdiv_basic_115200(dut):
    """Run 2000 cycles at 115,200 baud settings, verify against reference."""
    dut._log.info("115,200 baud (b=104, c=-18)")

    clock = Clock(dut.clk, 40, units="ns")  # 25 MHz
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    dut.b.value = 104
    dut.c.value = 238  # -18 as unsigned 8-bit
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    ref = ClkdivRef(104, 238)

    # Run and verify for 2000 cycles
    num_cycles = 2000
    for i in range(num_cycles):
        ref_output = ref.tick()
        dut_output = int(dut.q.value)

        assert ref_output == dut_output, (
            f"Mismatch at cycle {i}: ref={ref_output}, dut={dut_output}"
        )

        if (i + 1) % 500 == 0:
            dut._log.info(f"✓ Verified {i + 1} cycles")

        await ClockCycles(dut.clk, 1)

    dut._log.info(f"✓ All {num_cycles} cycles match reference model")


@cocotb.test()
async def test_clkdiv_basic_230400(dut):
    """Run 2000 cycles at 230,400 baud settings, verify against reference."""
    dut._log.info("230,400 baud (b=43, c=-18)")

    clock = Clock(dut.clk, 40, units="ns")  # 25 MHz
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    dut.b.value = 43
    dut.c.value = 238  # -18 as unsigned 8-bit
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    ref = ClkdivRef(43, 238)

    # Run and verify for 2000 cycles
    num_cycles = 2000
    for i in range(num_cycles):
        ref_output = ref.tick()
        dut_output = int(dut.q.value)

        assert ref_output == dut_output, (
            f"Mismatch at cycle {i}: ref={ref_output}, dut={dut_output}"
        )

        if (i + 1) % 500 == 0:
            dut._log.info(f"✓ Verified {i + 1} cycles")

        await ClockCycles(dut.clk, 1)

    dut._log.info(f"✓ All {num_cycles} cycles match reference model")


@cocotb.test()
async def test_clkdiv_frequency_115200(dut):
    """Measure output frequency at 115,200 baud, should be ~1.844 MHz."""
    dut._log.info("Frequency check: 115,200 baud")

    clock = Clock(dut.clk, 40, units="ns")  # 25 MHz
    cocotb.start_soon(clock.start())

    # Reset with 115,200 parameters
    dut.rst_n.value = 0
    dut.b.value = 104
    dut.c.value = 238
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    # Measure frequency over 100,000 cycles
    measurement_cycles = 100_000
    toggles = 0
    prev_q = 0

    await ClockCycles(dut.clk, 1)  # Skip first cycle after reset

    for _ in range(measurement_cycles):
        curr_q = int(dut.q.value)
        if curr_q != prev_q:
            toggles += 1
        prev_q = curr_q
        await ClockCycles(dut.clk, 1)

    # Each toggle is half a period, so toggles/2 = complete periods
    measured_ratio = (toggles / 2) / measurement_cycles

    # Expected: 1.844 MHz / 25 MHz = 0.07376
    expected_ratio = 1.844e6 / 25e6
    error_percent = abs(measured_ratio - expected_ratio) / expected_ratio * 100

    dut._log.info(f"Measured frequency ratio: {measured_ratio:.6f}")
    dut._log.info(f"Expected frequency ratio: {expected_ratio:.6f}")
    dut._log.info(f"Error: {error_percent:.2f}%")

    # Allow 5% measurement error (due to finite sampling)
    assert error_percent < 5.0, (
        f"Frequency error {error_percent:.2f}% exceeds 5% tolerance"
    )
    dut._log.info("✓ Frequency within tolerance")


@cocotb.test()
async def test_clkdiv_frequency_230400(dut):
    """Measure output frequency at 230,400 baud, should be ~3.689 MHz."""
    dut._log.info("Frequency check: 230,400 baud")

    clock = Clock(dut.clk, 40, units="ns")  # 25 MHz
    cocotb.start_soon(clock.start())

    # Reset with 230,400 parameters
    dut.rst_n.value = 0
    dut.b.value = 43
    dut.c.value = 238
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    # Measure frequency over 100,000 cycles
    measurement_cycles = 100_000
    toggles = 0
    prev_q = 0

    await ClockCycles(dut.clk, 1)  # Skip first cycle after reset

    for _ in range(measurement_cycles):
        curr_q = int(dut.q.value)
        if curr_q != prev_q:
            toggles += 1
        prev_q = curr_q
        await ClockCycles(dut.clk, 1)

    # Each toggle is half a period
    measured_ratio = (toggles / 2) / measurement_cycles

    # Expected: 3.689 MHz / 25 MHz = 0.14756
    expected_ratio = 3.689e6 / 25e6
    error_percent = abs(measured_ratio - expected_ratio) / expected_ratio * 100

    dut._log.info(f"Measured frequency ratio: {measured_ratio:.6f}")
    dut._log.info(f"Expected frequency ratio: {expected_ratio:.6f}")
    dut._log.info(f"Error: {error_percent:.2f}%")

    # Allow 5% measurement error
    assert error_percent < 5.0, (
        f"Frequency error {error_percent:.2f}% exceeds 5% tolerance"
    )
    dut._log.info("✓ Frequency within tolerance")


@cocotb.test()
async def test_clkdiv_parameter_change(dut):
    """Run at one setting, then switch parameters and run again."""
    dut._log.info("Parameter switching")

    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Start with 115,200 parameters
    dut.rst_n.value = 0
    dut.b.value = 104
    dut.c.value = 238
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    ref1 = ClkdivRef(104, 238)

    # Run 1000 cycles and verify
    for i in range(1000):
        ref_output = ref1.tick()
        dut_output = int(dut.q.value)
        assert ref_output == dut_output, f"Mismatch at cycle {i}"
        await ClockCycles(dut.clk, 1)

    dut._log.info("✓ First 1000 cycles verified with (104, 238)")

    # Change parameters to 230,400
    dut.b.value = 43
    dut.c.value = 238

    ref2 = ClkdivRef(43, 238)

    # Run another 1000 cycles with new parameters
    for i in range(1000):
        ref_output = ref2.tick()
        dut_output = int(dut.q.value)
        assert ref_output == dut_output, (
            f"Mismatch at cycle {i} after parameter change"
        )
        await ClockCycles(dut.clk, 1)

    dut._log.info("✓ Second 1000 cycles verified with (43, 238)")
    dut._log.info("✓ Parameter changes work correctly")


@cocotb.test()
async def test_clkdiv_edge_case_b_equals_neg_c(dut):
    """Test when b = -c (divides by 4)."""
    dut._log.info("Edge case: b = -c")

    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # b = -c means b = 18, c = 238 (-18 in signed)
    dut.rst_n.value = 0
    dut.b.value = 18
    dut.c.value = 238  # -18
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    ref = ClkdivRef(18, 238)

    # Run and verify
    for i in range(1000):
        ref_output = ref.tick()
        dut_output = int(dut.q.value)
        assert ref_output == dut_output, f"Mismatch at cycle {i}"
        await ClockCycles(dut.clk, 1)

    # Measure frequency - should be 25 MHz / 4 = 6.25 MHz
    toggles = 0
    prev_q = int(dut.q.value)

    for _ in range(1000):
        curr_q = int(dut.q.value)
        if curr_q != prev_q:
            toggles += 1
        prev_q = curr_q
        await ClockCycles(dut.clk, 1)

    measured_ratio = (toggles / 2) / 1000
    expected_ratio = 1.0 / 4  # 6.25 MHz / 25 MHz

    dut._log.info(f"Measured ratio: {measured_ratio:.6f}, Expected: {expected_ratio:.6f}")

    # Should be very close to 0.25
    assert abs(measured_ratio - expected_ratio) < 0.01, (
        f"Ratio mismatch for b=-c case"
    )
    dut._log.info("✓ Edge case b = -c verified")
