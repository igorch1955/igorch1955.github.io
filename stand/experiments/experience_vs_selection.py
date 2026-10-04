"""Experience or selection? Within the same individual: the peak of hunger and the day
of the first meal not from hunting, in the first and in the second hard times.

Run:  python3 experience_vs_selection.py [individuals] [out.json]
"""
from __future__ import annotations
import sys
import json
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from common import LIMIT, hard_periods
import main

per = hard_periods()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 90
out = []
for _ in range(n):
    s = main.Simulation()
    peak = [0.0] * len(per)
    first = [None] * len(per)
    with ThreadPoolExecutor(len(s.parallel)) as pool:
        while s.world.alive and s.tick < LIMIT:
            s.step(pool)
            h = s.history[-1]
            t = h["tick"]
            for k, (a, b) in enumerate(per):
                if a <= t < b:
                    peak[k] = max(peak[k], h["hunger"])
                    if first[k] is None and any(e.startswith(("catch", "drank")) and "hunting" not in e
                                                for e in h["events"]):
                        first[k] = t - a
    out.append(dict(life=s.tick, peak=peak, first=first))
with open(sys.argv[2] if len(sys.argv) > 2 else "experience_vs_selection.json", "w") as f:
    json.dump(out, f)

two = [r for r in out if r["life"] > per[1][1]]
p1 = np.array([r["peak"][0] for r in two])
p2 = np.array([r["peak"][1] for r in two])
print(f"individuals {n}; survived two hard times: {len(two)}")
print(f"peak hunger: first {np.median(p1):.2f}, second {np.median(p2):.2f} (medians); "
      f"lower in the second: {int((p2 < p1).sum())} of {len(two)}")
try:
    from scipy.stats import wilcoxon
    print(f"Wilcoxon signed-rank p = {wilcoxon(p1, p2).pvalue:.1e}")
except ImportError:
    pass
f = [(r["first"][0], r["first"][1]) for r in two if r["first"][0] is not None and r["first"][1] is not None]
if f:
    f1 = np.array([a for a, _ in f]) / 24
    f2 = np.array([b for _, b in f]) / 24
    print(f"first meal not from hunting: first {np.median(f1):.1f} days, second {np.median(f2):.1f} days; "
          f"earlier in the second: {int((f2 < f1).sum())} of {len(f)}")
