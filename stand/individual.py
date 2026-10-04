"""The individual: its graphs, the capacity to give rise to the new, and the executor.

Every part follows one contract:  step(percept, world_view) -> TickOutput.
A part never touches another part's state and never calls another part; the main
loop applies its requests (a push on the ball, a birth of a graph).

Graph  = what states and transitions a business has (hunting, sleep, tree, ...).
Matrix = what is known about each state. In this program a graph's matrix holds its
expectation E (how much relief one hour of effort brings) and, for "mushrooms",
the entries "A safe" / "B dangerous".

The six channels through which the individual's rules change during life
(there are no others):
  1. expectation of a way, E_g, updated by hours of effort;
  2. length of memory (experience counter n_g; step 1/(n+1), never below 1/72 per hour);
  3. return of hunting toward the innate expectation while hunting is not used;
  4. birth of a graph: in agony (BirthInAgony) or by novelty (the neighbour, in world.py);
  5. entries in the matrix of graph "mushrooms" (in world.py);
  6. skill: successes on a way lower its danger for this individual (in world.py).
"""
from __future__ import annotations
import numpy as np

from signals import Percept, WorldView, Effort, BirthRequest, TickOutput
from noise import NoiseSource
from world import HUNGER, HUNTING, SLEEP, toward


# ------------------------------------------------ graphs that learn (reference version)
class Graphs:
    """Graphs of the individual, with memory of experience.

    Innate (experience of generations, set as calibration by the Agent):
      - a drive for food: slightly hungry -> almost full strength; just fed -> weak;
        stored food does not quench it (a wolf in a sheepfold);
      - the expectation of hunting E0 (what hunting gives in good times);
      - sleep: tiredness and "slept long ago".
    Learned during life: which way to use. The food drive goes to ONE way at a time
    (acts are discrete). Ways compete by weight; hunting is always open, other ways
    open only as far as hunting "is not working" (its expectation fell below innate).
    Commitment keeps an attempt going (positive feedback, 1 + kappa * closeness),
    but a new decision (after sleep, after a catch) is made by expectations only.
    """
    name = "graphs"
    A = 0.05                 # strength of a push
    E0 = 0.067               # innate expectation of hunting: catches per hour of hunting in good times
    KAPPA = 3.0              # commitment to the business at hand
    T_LONG = 36              # innate: "slept long ago" ~1.5 days
    SLEEP_LONG = 0.5         # extra pull to sleep if slept long ago
    SIGMA_NEW = 0.2          # spread of the inherited expectation of a newborn graph
    HUNT_FLOOR = 0.45        # memory of hunting never below 45 % of innate (the individual is a hunter)
    H_SAT = 0.1              # food drive is almost full already at this hunger
    L_TYP = 18               # hours in a typical attempt (measured in good times)
    N_INNATE = 5             # innate expectation weighs as 5 typical attempts
    T_MEM = 72               # memory horizon: ~3 days of effort
    W_RELIEF = 0.1 / 0.6     # water relieves hunger by 0.1 against 0.6 for food
    T_RETURN = 7 * 24        # unused hunting returns to innate expectation in ~a week

    def __init__(self, noise: NoiseSource | None = None):
        self.noise = noise
        self.E = {"hunting": self.E0}
        self.n = {"hunting": self.N_INNATE * self.L_TYP}   # innate weight, in hours
        self.leader = None                                 # graph of the current attempt

    def _learn_hour(self, g: str, c: float):
        """One hour of effort of graph g: c = relief this hour (1 = catch, 0 = nothing)."""
        if g not in self.E:
            return
        a = max(1.0 / (self.n[g] + 1), 1.0 / self.T_MEM)
        self.E[g] += a * (c - self.E[g])
        if g == "hunting":
            self.E[g] = max(self.E[g], self.HUNT_FLOOR * self.E0)
        self.n[g] += 1

    def _sync(self, w: WorldView):
        """A newborn graph inherits the innate expectation, with spread and noise."""
        for nm in w.names[3:]:
            if nm not in self.E:
                z = float(self.noise.normal(1)[0]) if self.noise else 0.0
                self.E[nm] = max(1e-4, self.E0 * (1 + self.SIGMA_NEW * z))
                self.n[nm] = self.L_TYP        # inherited expectation weighs one typical attempt

    def step(self, p: Percept, w: WorldView) -> TickOutput:
        out, b = TickOutput(), p.body
        if not b.alive:
            return out
        self._sync(w)
        pos = w.position
        asleep = b.since_sleep == 0            # the individual knows it sleeps; sleep hours are not effort
        pulls = {}
        # innate food drive
        drive = self.A * min(1.0, b.hunger / self.H_SAT)
        # how far hunting "is not working": 0 at innate expectation, 1 at the floor
        drop = float(np.clip((self.E0 - self.E["hunting"]) / (self.E0 * (1 - self.HUNT_FLOOR)),
                             0.0, 1.0))
        weight = {g: e * (1.0 if g == "hunting" else drop) for g, e in self.E.items()}
        tot = sum(weight.values())
        # one drive, one way: commitment helps only the attempt already under way
        score = {g: (weight[g] / tot) * (1 + (self.KAPPA * pos[w.names.index(g)]
                                              if g == self.leader else 0.0)) for g in self.E}
        best = max(score, key=score.get)
        for g in self.E:
            pulls[g] = drive * (1 + self.KAPPA * pos[w.names.index(g)]) if g == best else 0.0
        u_sleep = b.fatigue + (self.SLEEP_LONG if b.since_sleep > self.T_LONG else 0.0)
        pulls["sleep"] = self.A * u_sleep * (1 + self.KAPPA * pos[SLEEP])
        # attempts: the strongest pull leads; an attempt ends with a catch or when another pull wins
        caught = p.event is not None and (p.event.kind.startswith("catch")
                                          or p.event.kind.startswith("drank"))
        leader = max(pulls, key=pulls.get)
        if self.leader is not None:
            hit = caught and p.event.kind == f"catch: {self.leader}"
            drank = (self.leader == "water" and p.event is not None
                     and p.event.kind.startswith("drank"))
            hit = hit or drank
            if not asleep and self.leader != "sleep":
                c = (self.W_RELIEF if drank else 1.0) if hit else 0.0
                self._learn_hour(self.leader, c)
            if hit or leader != self.leader:
                self.leader = None
        if self.leader is None:
            self.leader = leader
        if self.leader != "hunting":           # innate returns: the individual is a hunter
            self.E["hunting"] += (self.E0 - self.E["hunting"]) / self.T_RETURN
        # all pushes are added on the executor (no arbiter)
        for g, f in pulls.items():
            k = SLEEP if g == "sleep" else w.names.index(g)
            out.efforts.append(Effort(f"graph '{g}'", toward(pos, k, f)))
        return out


# ------------------------------------------------ graphs without memory (for comparison)
class GraphsWithoutMemory:
    """Comparison individual: the same body, the same capacity to give rise to the new,
    but its graphs keep no memory of experience. A fixed innate rule with the escalation
    "old hunting -> a way that has worked before -> (new graph, born elsewhere)",
    with hysteresis on the crisis and sleep thresholds."""
    name = "graphs without memory"
    A = 0.05
    ALARM = 0.3                  # crisis: closeness to Hunger above this
    EXIT = 0.15                  # leaves crisis below this (or after eating)
    T_LONG = 36                  # "slept long ago"
    F_TIRED, F_RESTED = 0.5, 0.2 # go to sleep / get up
    T_TRY = 30                   # ticks of trying old hunting in a crisis

    def __init__(self):
        self.crisis = 0
        self.in_crisis = False
        self.sleeping = False

    def step(self, p: Percept, w: WorldView) -> TickOutput:
        out, b = TickOutput(), p.body
        if not b.alive:
            return out
        pos = w.position
        if not self.in_crisis and pos[HUNGER] > self.ALARM:
            self.in_crisis = True
        elif self.in_crisis and (b.since_eat == 0 or pos[HUNGER] < self.EXIT):
            self.in_crisis = False
        born = list(w.names[3:])
        proven = [nm for nm in born if w.successes.get(nm, 0) > 0]
        newest = max(born, key=lambda nm: w.born_at[nm]) if born else None
        if newest and w.successes.get(newest, 0) == 0 \
                and p.tick - w.born_at[newest] < self.T_TRY:
            target = w.names.index(newest)       # a newborn graph is tried at once
        elif self.in_crisis:
            self.crisis += 1
            if b.since_sleep > self.T_LONG:
                target = SLEEP
            elif proven and self.crisis >= self.T_TRY:
                best = max(proven, key=lambda nm: w.successes[nm])
                target = w.names.index(best)     # a way that has worked before
            else:
                target = HUNTING                 # old hunting
        else:
            self.crisis = 0
            if not self.sleeping and b.fatigue > self.F_TIRED:
                self.sleeping = True
            elif self.sleeping and b.fatigue < self.F_RESTED:
                self.sleeping = False
            if self.sleeping:
                target = SLEEP
            elif b.food == 0:
                target = HUNTING
            else:
                target = SLEEP
        out.efforts.append(Effort(self.name, toward(pos, target, self.A)))
        return out


# ------------------------------------------------ the capacity to give rise to the new
class BirthInAgony:
    """Birth of a new graph in agony: only at the very edge. The ball is close to Hunger
    (threshold with noise), the body is hungry, nothing has been eaten for long, and
    neither old hunting nor a way that has worked before has helped. While life is
    bearable there are no new ideas. All thresholds are calibration by the Agent."""
    name = "birth in agony"
    EDGE = 0.4               # edge: closeness to Hunger (works in the window 0.35-0.45)
    SIGMA = 0.03             # noise on the edge
    T_DESPERATE = 60         # ticks without food
    T_PROVEN = 120           # extra wait if a way has worked before
    H_AGONY = 0.4            # agony needs a hungry body (~8 days without food)
    T_COOL = 200             # ticks between births

    def __init__(self, noise: NoiseSource, enabled: bool = True):
        self.noise, self.enabled = noise, enabled
        self.last_birth = -10 ** 9

    def step(self, p: Percept, w: WorldView) -> TickOutput:
        out, b = TickOutput(), p.body
        if not (self.enabled and b.alive):
            return out
        edge = self.EDGE + float(self.noise.normal(1, self.SIGMA)[0])
        proven = any(w.successes.get(nm, 0) > 0 for nm in w.names[3:])
        wait = self.T_DESPERATE + (self.T_PROVEN if proven else 0)
        if (w.position[HUNGER] > edge and b.since_eat > wait and b.hunger > self.H_AGONY
                and p.tick - self.last_birth > self.T_COOL):
            self.last_birth = p.tick
            out.births.append(BirthRequest(self.name, float(w.position[HUNGER])))
        return out


# ------------------------------------------------ the executor (the body's muscles)
class Executor:
    """Adds all pushes (no arbiter), sets the body's full strength, adds permanent noise.
    A tie is resolved by noise; the order of addition is the order of arrival."""
    name = "executor"
    SIGMA = 0.004            # permanent noise
    MAX = 0.05               # body strength: the resulting push always has this length

    def __init__(self, noise: NoiseSource):
        self.noise = noise

    def act(self, efforts: list[Effort], dim: int) -> np.ndarray:
        total = np.zeros(dim)
        for e in efforts:
            v = e.vector[:dim]
            total[:len(v)] += v
        norm = np.linalg.norm(total)
        if norm > 1e-12:
            total *= self.MAX / norm
        n = self.noise.normal(dim, self.SIGMA)
        return total + (n - n.mean())
