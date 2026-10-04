"""Shared helpers for the experiments: hard-time periods, one life, a series."""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from world import WorldParams          # noqa: E402
import main                            # noqa: E402

P = WorldParams()
LIMIT = P.age_max + 1


def hard_periods(prm: WorldParams = P):
    """(start, end) ticks of every hard-time period within a lifespan."""
    out, t = [], 0
    while t < prm.age_max:
        a = (t // prm.cycle) * prm.cycle + prm.hard_from
        if a >= prm.age_max:
            break
        out.append((a, min(a + prm.hard_len, prm.age_max)))
        t = (t // prm.cycle + 1) * prm.cycle
    return out


def one_life(**kw) -> dict:
    """Life span, cause of death and number of graph births of one individual."""
    s = main.Simulation(**kw)
    s.run(LIMIT)
    return dict(life=s.tick, cause=s.world.death_cause or "alive",
                births=sum(1 for line in s.log.lines if "GRAPH BIRTH" in line))


def survival_by_period(runs: list[dict]):
    """For each hard-time period: (entered alive, survived)."""
    rows = []
    for a, b in hard_periods():
        entered = [r for r in runs if r["life"] > a]
        rows.append((len(entered), sum(r["life"] > b for r in entered)))
    return rows
