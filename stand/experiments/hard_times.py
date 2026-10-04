"""Several hard times in one life: does survival grow with experience?
(Chapter 32: survival in the first to fourth hard times; table and figure 32.1.)

Variants:
  memory    - reference individual: capacity to give rise to the new + graphs with memory
  nomemory  - the same capacity, graphs without memory
  nobirth   - graphs with memory, no birth in agony (only what is learned by observation)

Run:  python3 hard_times.py <variant> [individuals] [tag]   -> results_<tag>.txt, <tag>.json
Percentages are of the individuals alive at the start of each hard-time period.
"""
from __future__ import annotations
import sys
import json
from collections import Counter
import numpy as np

from common import P, hard_periods, one_life, survival_by_period

VARIANTS = {
    "memory":   ("Finds its own and remembers", dict(birth=True, memory=True)),
    "nomemory": ("Finds its own but does not remember", dict(birth=True, memory=False)),
    "nobirth":  ("Only what is learned by observation", dict(birth=False, memory=True)),
}


def report(label: str, runs: list[dict]) -> str:
    per = hard_periods()
    old = sum(r["cause"] == "old age" for r in runs)
    life_pct = [100 * min(r["life"], P.age_max) / P.age_max for r in runs]
    gone = [r for r in runs if r["cause"] not in ("alive", "old age")
            and not any(a <= r["life"] <= b + 1 for a, b in per)]
    after = sum(1 for r in gone if any(b + 1 < r["life"] <= b + 240 for a, b in per))
    lines = [f"{label} ({len(runs)} individuals)",
             f"  lived out the full lifespan: {old}",
             f"  life, % of lifespan: median {np.median(life_pct):.0f}, mean {np.mean(life_pct):.0f}",
             f"  graphs born per individual: {np.mean([r['births'] for r in runs]):.1f}",
             f"  causes of death: {dict(Counter(r['cause'] for r in runs if r['cause'] not in ('alive', 'old age')))}",
             f"  died within 10 days after hard times (exhausted): {after}; in good times: {len(gone) - after}",
             "  hard times | entered | survived | share of entered"]
    for k, (e, s) in enumerate(survival_by_period(runs), 1):
        lines.append(f"      {k}      |  {e:>4}   |  {s:>4}    | " + (f"{100 * s / e:.0f} %" if e else "-"))
    return "\n".join(lines)


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "memory"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    tag = sys.argv[3] if len(sys.argv) > 3 else f"hard_times_{key}"
    label, kw = VARIANTS[key]
    runs = [one_life(**kw) for _ in range(n)]
    text = report(label, runs)
    print(text)
    with open(f"results_{tag}.txt", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(f"{tag}.json", "w", encoding="utf-8") as f:
        json.dump(runs, f)
