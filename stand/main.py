"""Main loop: one life of one individual in the simulated world.

One tick (one hour):
  1. The world takes the last push of the ball and returns the body and the events.
  2. The main event of the tick is chosen by priority.
  3. The parts of the individual (graphs; birth in agony) receive the same snapshot and
     work in parallel threads; their outputs arrive on a common bus in order of readiness.
  4. Requests are applied: birth of a new graph (the world offers an untried way).
  5. The executor adds all pushes, sets the body's strength and adds noise -> next push.
  6. Invariants are checked; the journal is written.
A life ends with death or at the tick limit.

Run:  python3 main.py [ticks]   - one life, journal in journal.txt
"""
from __future__ import annotations
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from signals import Percept, WorldView, TickOutput
from noise import NoiseSource
from world import World, WorldParams, HUNGER
from individual import Graphs, GraphsWithoutMemory, BirthInAgony, Executor

# priority of events when choosing the main event of a tick
PRIORITY = ["death", "catch", "drank", "observed", "neighbour died", "collapsed asleep",
            "ate from store", "woke up", "spoiled"]


def rank(kind: str) -> int:
    return next(i for i, p in enumerate(PRIORITY) if kind.startswith(p))


class Bus:
    """Common bus: parts write, the order of arrival is not fixed."""
    def __init__(self):
        self._lock = threading.Lock()
        self.out = TickOutput()

    def put(self, o: TickOutput):
        with self._lock:           # protects the lists, not the order
            self.out.efforts += o.efforts
            self.out.births += o.births


class Journal:
    """Plain-language journal of a life."""
    def __init__(self, path: str | None = None):
        self.lines: list[str] = []
        self.path = path

    def __call__(self, tick: int, text: str):
        self.lines.append(f"tick {tick}: {text}")

    def save(self):
        if self.path:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines) + "\n")


class InvariantError(AssertionError):
    pass


class Simulation:
    """One individual, one life.
    birth=True   - the individual has the capacity to give rise to the new (birth in agony);
    memory=True  - graphs keep memory of experience (reference individual);
    memory=False - graphs without memory (comparison individual)."""

    def __init__(self, journal: Journal | None = None, world_params: WorldParams | None = None,
                 birth: bool = True, memory: bool = True):
        self.noise = NoiseSource("hw")
        self.world = World(self.noise, world_params)
        self.graphs = Graphs(self.noise) if memory else GraphsWithoutMemory()
        self.birth = BirthInAgony(self.noise, enabled=birth)
        self.parallel = [self.graphs, self.birth]
        self.executor = Executor(self.noise)
        self.move = np.zeros(3)
        self.tick = 0
        self.log = journal or Journal()
        self.history: list[dict] = []

    def view(self) -> WorldView:
        w = self.world
        return WorldView(self.tick, w.p.copy(), tuple(w.names), dict(w.born_at), dict(w.successes))

    def step(self, pool: ThreadPoolExecutor):
        t = self.tick
        was_hard = self.world.hard_times()
        body, events = self.world.step(self.move)
        if self.world.hard_times() != was_hard:
            self.log(t, "hard times began" if not was_hard else "hard times ended")
        events.sort(key=lambda e: rank(e.kind))
        p = Percept(t, body, events[0] if events else None)
        w = self.view()

        bus = Bus()
        futures = [pool.submit(m.step, p, w) for m in self.parallel]
        for f in as_completed(futures):          # onto the bus in order of readiness
            bus.put(f.result())

        for req in bus.out.births:               # birth of a graph in agony
            name = self.world.add_way()
            self.log(t, f"GRAPH BIRTH '{name}' (closeness to hunger {req.strength:.2f}, "
                        f"hunger {body.hunger:.2f})" if name else "no untried ways left")

        self.move = self.executor.act(bus.out.efforts, len(self.world.p))
        self._check()
        for e in events:
            self.log(t, f"{e.kind} (hunger {body.hunger:.2f}, fatigue {body.fatigue:.2f}, "
                        f"closeness to hunger {self.world.p[HUNGER]:.2f}, store {body.food})")
        self.history.append(dict(tick=t, hunger=body.hunger, F=body.fatigue,
                                 hard=self.world.hard_times(),
                                 events=[e.kind for e in events]))
        self.tick += 1

    def _check(self):
        p = self.world.p
        if not (np.all(np.isfinite(p)) and np.all(p >= -1e-12) and abs(p.sum() - 1) < 1e-9):
            raise InvariantError(f"tick {self.tick}: ball outside the simplex {p}")
        if not 0 <= self.world.F <= 1 or not 0 <= self.world.H <= 1:
            raise InvariantError(f"tick {self.tick}: body out of bounds")
        if len(p) != len(self.world.names):
            raise InvariantError(f"tick {self.tick}: vertices and names disagree")

    def run(self, limit: int):
        with ThreadPoolExecutor(max_workers=len(self.parallel)) as pool:
            while self.world.alive and self.tick < limit:
                self.step(pool)
        self.log.save()
        return self.history


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else WorldParams().age_max + 1
    s = Simulation(Journal("journal.txt"))
    s.run(limit)
    print(f"lived {s.tick} ticks ({s.tick / 24:.0f} days); "
          f"{'died: ' + s.world.death_cause if not s.world.alive else 'alive'}")
    print("graphs:", s.world.names, "successes:", s.world.successes)
