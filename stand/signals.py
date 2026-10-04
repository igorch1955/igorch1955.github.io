"""Signals: everything that passes between the parts of the program.

Rule: the parts never call each other. Each tick a part receives the same read-only
snapshot (Percept + WorldView) and returns its outputs (TickOutput). The main loop
collects the outputs and applies them. Any part can therefore be tested alone by
feeding it a hand-made snapshot.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass(frozen=True)
class Event:
    """Something that happened in the world this tick, as a short label."""
    kind: str


@dataclass(frozen=True)
class Body:
    """What the individual knows about its own body."""
    hunger: float          # H, 0..1; grows every tick, falls only with food (or water)
    fatigue: float         # F, 0..1; grows while awake, falls in sleep
    food: int              # portions in store
    since_sleep: int       # ticks since last sleep (0 while asleep)
    since_eat: int         # ticks since last meal
    alive: bool


@dataclass(frozen=True)
class Percept:
    """What every part receives each tick."""
    tick: int
    body: Body
    event: Event | None    # the main event of the tick (by priority), if any


@dataclass(frozen=True)
class WorldView:
    """Read-only view of the individual's own state of choice."""
    tick: int
    position: np.ndarray        # the ball: barycentric coordinates over the vertices
    names: tuple[str, ...]      # vertex names: hunger, hunting, sleep, then born graphs
    born_at: dict               # born graph name -> tick of birth
    successes: dict             # graph name -> number of successes (own experience)


@dataclass(frozen=True)
class Effort:
    """A push on the ball from one source: a vector in the simplex plane (sum 0)."""
    source: str
    vector: np.ndarray


@dataclass(frozen=True)
class BirthRequest:
    """Request to give birth to a new graph (from despair / agony)."""
    source: str
    strength: float             # closeness to the Hunger vertex at the moment


@dataclass
class TickOutput:
    """Everything the parts returned this tick, in order of arrival."""
    efforts: list[Effort] = field(default_factory=list)
    births: list[BirthRequest] = field(default_factory=list)
