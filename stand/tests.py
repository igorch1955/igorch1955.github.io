"""Control cases with a known answer (debug mode: one part + a hand-made surrounding).
Noise is either recorded and replayed, or zero.

Run:  python3 tests.py
"""
from __future__ import annotations
import numpy as np

from signals import Body, Percept, WorldView, Effort
from noise import NoiseSource
from world import World, WorldParams, Way, toward, HUNGER, HUNTING, SLEEP
from individual import Graphs, GraphsWithoutMemory, BirthInAgony, Executor

ZERO = NoiseSource("replay", replay=[0.0] * 100000)


def body(hunger=0.1, fatigue=0.1, food=0, since_sleep=0, since_eat=0):
    return Body(hunger, fatigue, food, since_sleep, since_eat, True)


def view(pos, names=("hunger", "hunting", "sleep"), born=None, succ=None, tick=0):
    return WorldView(tick, np.array(pos, float), tuple(names), born or {}, succ or {})


def check(name, ok):
    print(f"{'OK  ' if ok else 'FAIL'}  {name}")
    return bool(ok)


def main():
    R = []

    # 1. recorded noise replays bit for bit
    rec = NoiseSource("hw", record=True)
    a = rec.normal(50).tolist()
    b = NoiseSource("replay", replay=rec.recorded).normal(50).tolist()
    R.append(check("noise: a recorded stream replays bit for bit", a == b))

    # 2. executor: opposite pushes cancel; live noise resolves the tie; push stays in the plane
    v = np.array([0.0, 1.0, -1.0])
    a0 = Executor(ZERO).act([Effort("A", v), Effort("B", -v)], 3)
    a1 = Executor(NoiseSource("hw")).act([Effort("A", v), Effort("B", -v)], 3)
    R.append(check("executor: opposite pushes -> 0 with zero noise", np.allclose(a0, 0)))
    R.append(check("executor: a tie is resolved by noise", np.linalg.norm(a1) > 0))
    R.append(check("executor: push in the simplex plane (sum 0)", abs(a1.sum()) < 1e-12))

    # 3. world: no effort, no food -> death by starvation, not earlier and not of anything else
    w = World(ZERO, WorldParams(q_hard=1.0))
    t = 0
    while w.alive and t < 5000:
        w.step(np.zeros(3)); t += 1
    R.append(check(f"world: idleness -> death by starvation (tick {t})",
                   not w.alive and w.death_cause == "starvation"))

    # 4. world: sleep does not feed
    w = World(ZERO, WorldParams())
    for _ in range(300):
        w.step(toward(w.p, SLEEP, 0.03))
    R.append(check(f"world: sleep does not feed (hunger after 300 ticks of sleep {w.H:.2f})", w.H > 0.5))

    # 5. world: a fed hunter touches Hunting -> catch
    w = World(ZERO, WorldParams(q_hard=1.0))
    kinds = []
    for _ in range(200):
        _, ev = w.step(toward(w.p, HUNTING, Graphs.A)); kinds += [e.kind for e in ev]
        if any(k.startswith("catch") for k in kinds):
            break
    R.append(check("world: a fed hunter -> catch", "catch: hunting" in kinds))

    # 6. world: a way with risk 1 -> death on touch; with risk 0 -> catch
    for risk, want in ((1.0, "death"), (0.0, "catch")):
        w = World(ZERO, WorldParams(ways=(Way("x", 1.5, risk, "died"),)))
        w.add_way()
        kinds = []
        for _ in range(300):
            _, ev = w.step(toward(w.p, 3, 0.03)); kinds += [e.kind for e in ev]
            if kinds:
                break
        R.append(check(f"world: risk {risk} -> {want}", kinds and kinds[0].startswith(want)))

    # 7. birth in agony: off - silent at the edge; on - birth at the edge; silent while life is bearable
    edge = view([0.95, 0.03, 0.02])
    p_edge = Percept(1000, body(0.9, 0.3, 0, 0, 500), None)
    R.append(check("birth in agony off: silence at the edge",
                   BirthInAgony(ZERO, enabled=False).step(p_edge, edge).births == []))
    R.append(check("birth in agony on: birth at the edge",
                   len(BirthInAgony(ZERO).step(p_edge, edge).births) == 1))
    R.append(check("birth in agony on: silence while life is bearable",
                   BirthInAgony(ZERO).step(Percept(10, body(0.2), None),
                                           view([0.3, 0.35, 0.35])).births == []))

    # 8. graphs without memory: no chatter at the threshold (hysteresis); a newborn graph is tried at once
    g = GraphsWithoutMemory()
    targets = []
    for k in range(40):
        h = 0.5 + 0.02 * (-1) ** k
        pos = [h, (1 - h) / 2, (1 - h) / 2]
        e = g.step(Percept(k, body(0.4, 0.2, 0, 10, 100), None), view(pos))
        targets.append(int(np.argmax(e.efforts[0].vector)))
    R.append(check("graphs without memory: no chatter at the threshold", len(set(targets[1:])) == 1))
    names = ("hunger", "hunting", "sleep", "mushrooms")
    e = g.step(Percept(500, body(0.2, 0.1, 0, 10, 100), None),
               view([0.3, 0.3, 0.3, 0.1], names, {"mushrooms": 495}, {"mushrooms": 0}, 500))
    R.append(check("graphs without memory: a newborn graph is tried at once",
                   int(np.argmax(e.efforts[0].vector)) == 3))

    # 9. graphs with memory: in good times all food effort goes to hunting
    gm = Graphs(ZERO)
    e = gm.step(Percept(10, body(0.3, 0.1, 0, 10, 50), None),
                view([0.3, 0.3, 0.3, 0.1], names, {"mushrooms": 5}, {"mushrooms": 0}, 10))
    pushes = {x.source: np.linalg.norm(x.vector) for x in e.efforts}
    R.append(check("graphs with memory: in good times the drive goes to hunting only",
                   pushes["graph 'hunting'"] > 0 and pushes["graph 'mushrooms'"] == 0))

    # 10. mushrooms: the kind is chosen by the entries in the matrix of graph "mushrooms"
    def poisonings(records, n=400):
        dead = 0
        for _ in range(n):
            w = World(NoiseSource("hw"), WorldParams())
            w._add_named("mushrooms")
            w.mush = dict(records)
            k = w.names.index("mushrooms")
            w.p = np.zeros(len(w.p)); w.p[k] = 1.0
            w.step(np.zeros(len(w.p)))
            dead += w.death_cause == "poisoned"
        return dead / n
    R.append(check("mushrooms: knows 'A safe' -> never poisoned", poisonings({"A": "safe"}) == 0))
    R.append(check("mushrooms: knows 'B dangerous' -> never poisoned", poisonings({"B": "dangerous"}) == 0))
    d = poisonings({})
    R.append(check(f"mushrooms: knows nothing -> poisoned ~40 % (got {d:.0%})", 0.3 < d < 0.5))

    print(f"\ntotal: {sum(R)} of {len(R)}")


if __name__ == "__main__":
    main()
