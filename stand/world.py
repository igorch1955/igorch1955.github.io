"""The simulated world and the individual's body.

Only the world knows its own rules and numbers (how much hunting yields, how dangerous a
tree is). The individual sees its body and its own experience, never these numbers.

Time scale: one tick = one hour; a day = 24 ticks.

The individual's choice is a ball in a simplex. Fixed vertices:
  HUNGER  - touching it means death by starvation;
  HUNTING - touching it means a catch (food);
  SLEEP   - coming close to it means falling asleep.
Graphs born during life add vertices (tree, water, mushrooms).
The ball moves continuously; acts and states (catch, sleep, death) are discrete.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from signals import Event, Body
from noise import NoiseSource

HUNGER, HUNTING, SLEEP = 0, 1, 2          # fixed vertices


def project_simplex(v: np.ndarray) -> np.ndarray:
    """Euclidean projection onto the simplex (all >= 0, sum 1)."""
    u = np.sort(v)[::-1]
    css = np.cumsum(u) - 1.0
    k = np.nonzero(u - css / np.arange(1, len(v) + 1) > 0)[0][-1]
    return np.maximum(v - css[k] / (k + 1), 0.0)


def toward(p: np.ndarray, vertex: int, amount: float) -> np.ndarray:
    """A shift of length `amount` from p toward a vertex (components sum to 0)."""
    d = -p.copy()
    d[vertex] += 1.0
    n = np.linalg.norm(d)
    return np.zeros(len(p)) if n < 1e-12 else d / n * amount


@dataclass(frozen=True)
class Way:
    """A way of getting food (or relief) that the individual has never tried.
    Its properties are known only to the world."""
    name: str
    ease: float           # how fast the ball moves toward this vertex (hunting = 1)
    risk: float           # probability of death on each touch (before skill)
    death: str            # cause of death if it happens


WORLD_WAYS = (
    Way("tree", 1.3, 0.15, "fell from a tree"),
    Way("water", 1.3, 0.20, "drowned"),          # water does not feed; see water_relief
    Way("mushrooms", 1.5, 0.0, "poisoned"),       # one graph; kinds A/B are matrix entries
)
MUSHROOM_POISON = 0.8     # eating a kind-B (poisonous) mushroom kills with this probability


@dataclass
class WorldParams:
    """World passport (frozen reference version). Every number is the world's, not the individual's."""
    # body scale: one tick = one hour; without food the body lasts ~20 days
    h_rate: float = 1 / 480      # hunger growth per tick: 0 -> 1 in ~20 days
    g0: float = 0.001            # pull toward Hunger when fed
    gmax: float = 0.02           # pull toward Hunger grows and saturates: g = g0 + gmax * H^3
    eps: float = 0.02            # "touch": distance to a vertex below this
    K: int = 3                   # portions per catch (one eaten at once, the rest stored)
    e: float = 0.6               # hunger relief per portion (H -= e)
    c: float = 0.5               # after a catch this share of the way's coordinate moves to Sleep
    T_spoil: int = 240           # stored food spoils after ~10 days
    h_eat: float = 0.5           # eats from store when hunger is above this
    # fatigue and sleep
    f0: float = 1 / 72           # waking fatigue: 0 -> 1 in 3 days; at 1 sleep comes by force
    f_o: float = 0.2             # extra fatigue from effort (times the flow toward a way)
    sleep_h: float = 6.0         # mean sleep, hours
    k_F: float = 0.8             # fatigue lengthens sleep: x (1 + 0.8 F); after 3 days awake ~11 h
    k_food: float = 0.15         # fed +15 %, very hungry -15 %: x (1 + 0.15 (1 - 2H))
    debt_F: float = 2 / 3        # awake >= 2 days (F >= 2/3): one night restores 85 %, the rest next night
    debt_part: float = 0.85
    R: float = 0.5               # radius of the sleep zone (relative closeness to Sleep)
    w: float = 0.4               # push on waking (half to Hunting, half to Hunger)
    collapse: float = 0.5        # F = 1: forced fall toward Sleep
    fall_asleep: float = 0.5     # falls asleep when sleep depth >= this
    # hard times
    cycle: int = 2400            # one cycle ~100 days
    hard_from: int = 700         # hard times start inside the cycle
    hard_len: int = 720          # and last ~30 days
    q_hard: float = 0.2          # hunting yield in hard times (normal = 1)
    ways: tuple = WORLD_WAYS
    # stress
    adr_from: float = 0.3        # adrenaline starts when closeness to Hunger is above this
    adr_gain: float = 1.0        # strength x (1 + adrenaline); up to adr_gain at the edge
    adr_cost: float = 0.005      # price: extra fatigue per tick x adrenaline
    adr_up: float = 5.0          # release time constant, ticks
    adr_down: float = 24.0       # clearance time constant (~a day)
    insight: float = 0.6         # insight: at the birth of a graph the ball jumps this share toward it
    age_max: int = 400 * 24      # lifespan limit: 400 days
    # the neighbour (a random event instead of a herd): about once in 15 days
    p_witness: float = 1 / (15 * 24)
    # what is seen: neighbour poisoned by B / neighbour ate A and is fine / other deaths
    witness_causes: tuple = (("B", 0.8), ("A", 0.8), ("tree", 0.15), ("water", 0.2), ("hunger", 0.3))
    # mushrooms are scarce; water does not feed but prolongs life
    mush_max: int = 2            # a full patch holds 2 meals
    mush_regrow: int = 20 * 24   # one meal grows back in ~3 weeks
    water_relief: float = 0.1    # drinking: no food, the body lives on its own reserves (H -= 0.1, ~2 days)


class World:
    """The world and the body of one individual."""
    name = "world"

    def __init__(self, noise: NoiseSource, prm: WorldParams | None = None):
        self.noise, self.P = noise, prm or WorldParams()
        self.names = ["hunger", "hunting", "sleep"]
        self.ways: dict[str, Way] = {}
        self.p = np.full(3, 1 / 3)               # the ball
        self.H = 0.0                             # hunger
        self.F = 0.0                             # fatigue
        self.A = 0.0                             # adrenaline (a body quantity with inertia)
        self.food_ages: list[int] = []           # stored portions and their ages
        self.sleep_run = self.since_sleep = self.since_eat = 0
        self.asleep = False
        self.mush_stock = self.P.mush_max        # mushroom patch is full
        self.t = 0
        self.alive = True
        self.death_cause = ""
        self.successes: dict[str, int] = {"hunting": 0}   # own successes per way (skill)
        self.mush: dict[str, str] = {}           # entries in the matrix of graph "mushrooms": kind -> "safe"/"dangerous"
        self.born_at: dict[str, int] = {}

    # --- helpers
    def hard_times(self) -> bool:
        P = self.P
        ph = self.t % P.cycle
        return P.hard_from <= ph < P.hard_from + P.hard_len

    def _ease(self, k: int) -> float:
        if k == HUNTING:
            return self.P.q_hard if self.hard_times() else 1.0
        name = self.names[k]
        if name == "mushrooms":                  # fewer mushrooms left -> harder to find
            return self.ways[name].ease * self.mush_stock / self.P.mush_max
        return self.ways[name].ease

    def _shift(self, frm: int, to: int, amount: float):
        amount = min(amount, self.p[frm])
        self.p[frm] -= amount
        self.p[to] += amount

    @staticmethod
    def _event(kind: str, detail: str = "") -> Event:
        return Event(kind + (f": {detail}" if detail else ""))

    def _eat(self):
        self.H = max(0.0, self.H - self.P.e)
        self.since_eat = 0

    def _die(self, cause: str, ev: list):
        self.alive = False
        self.death_cause = cause
        ev.append(self._event("death", cause))

    def _fall_asleep(self, ev):
        P = self.P
        if self.F >= 1.0:                        # lack of sleep does not kill: the body collapses into sleep
            for k in range(1, len(self.p)):
                if k != SLEEP:
                    self._shift(k, SLEEP, P.collapse * self.p[k])
            ev.append(self._event("collapsed asleep"))
        self.asleep = True
        self.sleep_run = 0
        self.sleep_F0 = self.F
        self.sleep_restore = self.F * (P.debt_part if self.F >= P.debt_F else 1.0)
        self.sleep_noise = 1.0 + 0.1 * float(self.noise.normal(1)[0])

    def body(self) -> Body:
        return Body(float(self.H), float(self.F), len(self.food_ages),
                    self.since_sleep, self.since_eat, self.alive)

    # --- birth of graphs
    def add_way(self) -> str | None:
        """Birth of a graph in agony: the world offers an untried way; noise decides which."""
        untried = [w for w in self.P.ways if w.name not in self.ways]
        if not untried:
            return None
        k = min(int(self.noise.uniform() * len(untried)), len(untried) - 1)
        way = untried[k]
        self.ways[way.name] = way
        self.names.append(way.name)
        self.p = np.append(self.p, 0.0)
        self.successes[way.name] = 0
        self.born_at[way.name] = self.t
        if self.P.insight > 0:                   # insight: the ball jumps close to the new vertex
            k = len(self.p) - 1
            self.p = (1 - self.P.insight) * self.p
            self.p[k] += self.P.insight
        return way.name

    def _add_named(self, name: str):
        """Birth of a graph by novelty (something never seen before): no jump of the ball."""
        way = next(w for w in self.P.ways if w.name == name)
        self.ways[way.name] = way
        self.names.append(way.name)
        self.p = np.append(self.p, 0.0)
        self.successes[way.name] = 0
        self.born_at[way.name] = self.t

    def _update_adrenaline(self):
        """Fast release near Hunger, slow clearance (a hormone has inertia)."""
        P = self.P
        x = (self.p[HUNGER] - P.adr_from) / (1.0 - P.adr_from)
        target = P.adr_gain * float(np.clip(x, 0.0, 1.0))
        tau = P.adr_up if target > self.A else P.adr_down
        self.A += (target - self.A) / tau

    def _pick_mushroom(self) -> str:
        """Which kind is picked: by the entries in the matrix of graph "mushrooms"."""
        cand = [k for k in ("A", "B") if self.mush.get(k) != "dangerous"]
        good = [k for k in cand if self.mush.get(k) == "safe"]
        pool = good or cand or ["A", "B"]
        return pool[min(int(self.noise.uniform() * len(pool)), len(pool) - 1)]

    # --- one tick
    def step(self, move: np.ndarray) -> tuple[Body, list[Event]]:
        P, ev, n = self.P, [], len(self.p)
        if not self.alive:
            return self.body(), ev
        self.t += 1
        self.since_sleep += 1
        self.since_eat += 1
        self.H = min(1.0, self.H + P.h_rate)

        # 1. the pull toward Hunger grows with hunger (taken from the other vertices pro rata)
        rest = 1.0 - self.p[HUNGER]
        if rest > 0:
            g = min(P.g0 + P.gmax * self.H ** 3, rest)
            take = self.p * (g / rest)
            take[HUNGER] = 0.0
            self.p -= take
            self.p[HUNGER] += g

        # 2. the individual's push: weakened by fatigue and difficulty, helped by adrenaline
        m = np.zeros(n)
        if not self.asleep:                      # a sleeping body does not move
            m[:min(n, len(move))] = move[:n]
        flow = 0.0
        self._update_adrenaline()
        adr = self.A
        for k in range(1, n):
            if k != SLEEP and m[k] > 0:
                new = m[k] * (1.0 - self.F ** 2) * (1.0 + adr) * min(self._ease(k), 1.5)
                flow += new
                cut = m[k] - new
                m[k] = new
                neg = np.where(m < 0, -m, 0.0)
                if neg.sum() > 0:
                    m += cut * neg / neg.sum()
        self.p = project_simplex(self.p + m)

        # 3. fatigue and sleep; closeness to Sleep is measured among activities (without Hunger):
        #    a hungry individual still dozes
        awake = 1.0 - self.p[HUNGER]
        d_S = 1.0 - (self.p[SLEEP] / awake if awake > 1e-9 else 0.0)
        depth = max(0.0, 1.0 - d_S / P.R)
        if not self.asleep and (depth >= P.fall_asleep or self.F >= 1.0):
            self._fall_asleep(ev)                # sleep is an act
        if self.asleep:
            D = (P.sleep_h * (1 + P.k_F * self.sleep_F0)
                 * (1 + P.k_food * (1 - 2 * self.H)) * self.sleep_noise)
            D = max(D, 1.0)                      # hunger shortens sleep as it goes
            self.F -= self.sleep_restore / D
            self.sleep_run += 1
            self.since_sleep = 0
            if self.sleep_run >= D:
                self.asleep = False
                self._shift(SLEEP, HUNTING, P.w / 2)
                self._shift(SLEEP, HUNGER, P.w / 2)
                self.sleep_run = 0
                ev.append(self._event("woke up"))
        else:
            self.F += P.f0 + P.f_o * flow + P.adr_cost * adr
        self.F = float(np.clip(self.F, 0.0, 1.0))

        # 4. touching a food vertex: a catch (or death, for risky ways)
        for k in range(1, len(self.p)):
            if k == SLEEP or 1.0 - self.p[k] >= P.eps:
                continue
            name = self.names[k]
            if name == "mushrooms":              # which kind is picked: by the matrix entries
                kind = self._pick_mushroom()
                if kind == "B" and self.noise.uniform() < MUSHROOM_POISON:
                    self._die("poisoned", ev)
                    return self.body(), ev
                if kind not in self.mush or self.mush[kind] != "dangerous":
                    self.mush[kind] = "safe"     # own lesson: ate and survived (can be a false lesson)
                self.mush_stock -= 1             # one meal eaten, the patch gets poorer
            elif k != HUNTING:
                risk = self.ways[name].risk / (1 + self.successes.get(name, 0))   # skill
                if self.noise.uniform() < risk:
                    self._die(self.ways[name].death, ev)
                    return self.body(), ev
            if name == "water":                  # not food: the body lives on its own reserves
                self.H = max(0.0, self.H - P.water_relief)
                self.successes[name] = self.successes.get(name, 0) + 1
                self._shift(k, SLEEP, P.c * self.p[k])
                ev.append(self._event("drank"))
                continue
            self.food_ages += [0] * (P.K - 1)
            self._eat()
            self.successes[name] = self.successes.get(name, 0) + 1
            self._shift(k, SLEEP, P.c * self.p[k])
            ev.append(self._event("catch", name))

        # 5. eating from store, spoilage
        if self.food_ages and self.H > P.h_eat:
            self.food_ages.pop(0)
            self._eat()
            ev.append(self._event("ate from store"))
        self.food_ages = [a + 1 for a in self.food_ages]
        if any(a > P.T_spoil for a in self.food_ages):
            self.food_ages = [a for a in self.food_ages if a <= P.T_spoil]
            ev.append(self._event("spoiled"))

        # 6. the mushroom patch grows back
        if self.mush_stock < P.mush_max and self.t % P.mush_regrow == 0:
            self.mush_stock += 1

        # 7. the neighbour: another's experience becomes an entry in a matrix
        if self.noise.uniform() < P.p_witness:
            names = [c for c, _ in P.witness_causes]
            wts = np.array([w for _, w in P.witness_causes], float)
            u = self.noise.uniform() * wts.sum()
            cause = names[min(int(np.searchsorted(np.cumsum(wts), u)), len(names) - 1)]
            if cause in ("A", "B"):
                rec = "safe" if cause == "A" else "dangerous"
                what = "neighbour ate A and is fine" if cause == "A" else "neighbour was poisoned by B"
                born = ""
                if "mushrooms" not in self.names:    # novelty: graph "mushrooms" is born
                    self._add_named("mushrooms")
                    born = "; GRAPH BIRTH 'mushrooms' (novelty)"
                self.mush[cause] = rec
                ev.append(self._event("observed", f"{what}; entry '{cause} {rec}'{born}"))
            else:
                ev.append(self._event("neighbour died", cause))

        # 8. old age
        if self.t >= P.age_max:
            self._die("old age", ev)
            return self.body(), ev

        # 9. death by starvation: touching Hunger, or full exhaustion H = 1 wherever the ball is
        if 1.0 - self.p[HUNGER] < P.eps or self.H >= 1.0:
            self._die("starvation", ev)

        return self.body(), ev
