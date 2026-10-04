# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

"""Reference model for clkdiv."""


class ClkdivRef:
    """Simulates the fractional clock divider.

    Accumulates b and c each cycle. When the accumulator MSB is set, we add b,
    otherwise c. Output toggles whenever the MSB becomes set.
    """

    def __init__(self, b: int, c: int) -> None:
        """Init with parameters.

        Args:
            b: Positive parameter (8-bit)
            c: Negative parameter as unsigned 8-bit two's complement
        """
        self.b = b & 0xFF
        self.c = c & 0xFF
        self.sr = 0  # 8-bit accumulator
        self.q = 0   # Output
        self._validate_params()

    def _validate_params(self) -> None:
        """Sanity check the parameters."""
        c_signed = self.c if self.c < 128 else self.c - 256
        b_signed = self.b if self.b < 128 else self.b - 256

        assert b_signed > 0, f"b must be > 0, got {b_signed}"
        assert c_signed < 0, f"c must be < 0, got {c_signed}"
        assert b_signed >= -c_signed, f"b ({b_signed}) must be >= -c ({-c_signed})"
        assert (b_signed - c_signed) <= 127, f"b - c must be <= 127, got {b_signed - c_signed}"

    def tick(self) -> int:
        """Run one cycle. Return the output."""
        d = self.b if (self.sr & 0x80) else self.c
        self.sr = (self.sr + d) & 0xFF
        if self.sr & 0x80:
            self.q ^= 1
        return self.q

    def measure_frequency(self, cycles: int) -> float:
        """Count toggles over N cycles, return frequency ratio."""
        toggles = 0
        for _ in range(cycles):
            prev_q = self.q
            self.tick()
            if self.q != prev_q:
                toggles += 1

        return (toggles / 2) / cycles if cycles > 0 else 0.0
