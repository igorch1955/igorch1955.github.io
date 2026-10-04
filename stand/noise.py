"""Source of randomness.

Noise is a permanent component of the program, not a reaction to a detected tie:
a pyramid cannot stand on its tip, so equal options are always resolved by noise.

Modes:
  "hw"     - hardware entropy of the operating system (os.urandom: RDRAND, device
             noise, kernel pool). Every value is new; a run cannot be repeated.
  "replay" - values are taken from a recorded stream (debugging a single module).
With record=True every value handed out is stored, so a module can be re-run
bit for bit from the recording.
"""
from __future__ import annotations
import os
from math import erf, sqrt
import numpy as np


class NoiseSource:
    def __init__(self, mode: str = "hw", replay: list[float] | None = None,
                 record: bool = False):
        assert mode in ("hw", "replay")
        self.mode = mode
        self._replay = list(replay or [])
        self._pos = 0
        self.recorded: list[float] | None = [] if record else None

    def _uniform(self, n: int) -> np.ndarray:
        raw = np.frombuffer(os.urandom(8 * n), dtype=np.uint64)
        return (raw >> np.uint64(11)).astype(np.float64) / float(1 << 53)

    def normal(self, n: int, sigma: float = 1.0) -> np.ndarray:
        """n standard normal values times sigma."""
        if self.mode == "replay":
            vals = np.array(self._replay[self._pos:self._pos + n], dtype=float)
            if len(vals) < n:
                raise RuntimeError("replay stream exhausted")
            self._pos += n
        else:
            # Box-Muller on hardware uniform numbers
            m = (n + 1) // 2
            u1 = np.clip(self._uniform(m), 1e-300, 1.0)
            u2 = self._uniform(m)
            r = np.sqrt(-2.0 * np.log(u1))
            vals = np.concatenate([r * np.cos(2 * np.pi * u2),
                                   r * np.sin(2 * np.pi * u2)])[:n]
        if self.recorded is not None:
            self.recorded.extend(vals.tolist())
        return vals * sigma

    def uniform(self) -> float:
        """Uniform value in 0..1 (normal value mapped through the error function)."""
        z = float(self.normal(1)[0])
        return 0.5 * (1.0 + erf(z / sqrt(2.0)))
