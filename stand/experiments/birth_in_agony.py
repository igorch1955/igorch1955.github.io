"""Birth of a new graph in agony: calibration of the world and the test.
(Chapter 32: does the capacity to give rise to the new help, and when?)

Calibration of the world (before testing the individual):
  c1_good    - no hard times, no birth in agony: everybody should live
  c2_hard    - hard times, nothing new at all (no birth, no neighbour): everybody should die
  c3_oracle  - an individual that knows the tree in advance: a way out must exist
Test:
  full       - birth in agony + adrenaline + insight (reference)
  insight    - only insight          adrenaline - only adrenaline
  nostress   - neither               nobirth    - no birth in agony (neighbour present)

Run:  python3 birth_in_agony.py <variant> [individuals]   -> birth_<variant>.json
"""
from __future__ import annotations
import sys
import json
from collections import Counter
import numpy as np

from common import LIMIT, hard_periods
import main
from world import WorldParams, WORLD_WAYS, SLEEP, HUNTING, toward
from individual import GraphsWithoutMemory
from signals import Effort, TickOutput


class Oracle(GraphsWithoutMemory):
    """Upper control: knows the world - the way out (tree) and when hard times come.
    Has food in store - rests; no food - hunts in good times, climbs the tree in hard
    times; tired - sleeps (with hysteresis)."""
    WAY = "tree"
    world = None

    def step(self, p, w):
        out, b = TickOutput(), p.body
        if not b.alive:
            return out
        if not self.sleeping and b.fatigue > self.F_TIRED:
            self.sleeping = True
        elif self.sleeping and b.fatigue < self.F_RESTED:
            self.sleeping = False
        if self.sleeping or b.food > 0:
            tgt = SLEEP
        elif self.world is not None and self.world.hard_times():
            tgt = w.names.index(self.WAY)
        else:
            tgt = HUNTING
        out.efforts.append(Effort("oracle", toward(w.position, tgt, self.A)))
        return out


VARIANTS = {
    "c1_good":    dict(birth=False, world=dict(q_hard=1.0)),
    "c2_hard":    dict(birth=False, world=dict(p_witness=0.0)),
    "c3_oracle":  dict(oracle=True),
    "full":       dict(birth=True, world=dict()),
    "insight":    dict(birth=True, world=dict(adr_gain=0.0)),
    "adrenaline": dict(birth=True, world=dict(insight=0.0)),
    "nostress":   dict(birth=True, world=dict(adr_gain=0.0, insight=0.0)),
    "nobirth":    dict(birth=False, world=dict()),
}


def one(v: dict) -> dict:
    if v.get("oracle"):
        s = main.Simulation(world_params=WorldParams(ways=(WORLD_WAYS[0],), p_witness=0.0), birth=False)
        s.world.add_way()                         # the tree is known from the start
        s.world.p = np.array([0.33, 0.33, 0.34, 0.0])
        o = Oracle()
        o.world = s.world
        s.graphs = o
        s.parallel[0] = o
    else:
        s = main.Simulation(world_params=WorldParams(**v["world"]), birth=v["birth"], memory=True)
    s.run(LIMIT)
    return dict(life=s.tick, cause=s.world.death_cause or "alive",
                births=sum(1 for line in s.log.lines if "GRAPH BIRTH" in line))


if __name__ == "__main__":
    key = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    runs = [one(VARIANTS[key]) for _ in range(n)]
    with open(f"birth_{key}.json", "w", encoding="utf-8") as f:
        json.dump(runs, f)
    first = hard_periods()[0][1]
    print(f"{key}: survived first hard times {sum(r['life'] > first for r in runs)}/{n}; "
          f"lived out the full lifespan {sum(r['cause'] == 'old age' for r in runs)}/{n}; "
          f"graphs born per individual {np.mean([r['births'] for r in runs]):.1f}; "
          f"deaths {dict(Counter(r['cause'] for r in runs if r['cause'] not in ('old age', 'alive')))}")
