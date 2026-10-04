# Appendix. How the program of the simulated world works

The program lives one life of one individual in a simulated world: up to 400 days, with a time step (tick) of one hour. The experiment of chapter 32 is hundreds of such lives, lived one after another. The program code is published on the author's website; this appendix describes what it does, without code.

## 1. What the program consists of

A diagram of the parts of the program and what they pass to each other is in chapter 32, section "How the simulated world and its inhabitant are built".

- **The simulated world and the individual's body.** The world knows its own rules: how much hunting yields, when hard times come, how dangerous a tree is. The body is hunger, fatigue and stored food. The individual does not know these rules; it sees only its body, what happened during the hour, and where its choice is now.
- **The individual**, two parts working at the same time:
  - **graphs with matrices**, the memory of experience: what to do and what to expect from it;
  - **the capacity to give rise to the new**: in agony a new graph is born.
- **The executor**, the "muscles". It adds up the pushes of all graphs, gives them the strength of the body and adds permanent noise.
- **The noise source**: hardware randomness of the computer itself.
- **The journal of a life**: events written down in plain words.

The parts never call one another. Every hour they receive the same picture and return their answers; whatever arrives first is added first.

## 2. One hour of life

1. **The world takes a step.** Hunger grows. The pull toward the Hunger vertex grows with hunger. The choice moves under the push the individual made in the previous hour; the push is weakened by fatigue and by the difficulty of the way, and strengthened by a surge of strength. Fatigue grows or is relieved; the individual falls asleep or wakes up. If the choice touches the vertex of a way, there is a catch (or death, if the way is dangerous). Eating from the store, spoilage, mushrooms growing back. Sometimes a meeting with the neighbour. Old age. Death by starvation.
2. **The main event of the hour is chosen** by importance: death, catch, drinking, something seen at the neighbour's, collapsing into sleep, eating from the store, waking up, spoilage.
3. **The individual thinks.** The graphs and the capacity to give rise to the new receive the same picture at the same time: the body, the main event, the position of choice, its own graphs and their successes.
4. **Birth of a new graph**, if the individual is in agony: the world offers one of the ways not yet tried; chance decides which.
5. **The executor** adds the pushes, gives them the body's strength and adds noise: this is the push of the next hour.
6. **Checks and the journal.** The program checks that the choice stays within its bounds and the body within its limits, and writes down the events.

## 3. How the individual is built

### The choice

The figure "the individual's choice as a ball in a triangle" is in chapter 32, same section.

The choice is a point (a ball) in a triangle with the vertices **Hunger**, **Hunting**, **Sleep**. The ball moves smoothly, while acts and states are discrete: touching Hunting is a catch; touching Hunger is death; coming close to Sleep is falling asleep. Each born graph (mushrooms, tree, water) adds a new vertex.

### Graphs and matrices

A **graph** is what states and transitions a business has (hunting, sleep, tree...). A **matrix** is what is known about each state. In the program a graph's matrix holds its **expectation**: how much relief one hour of effort brings. The matrix of graph "mushrooms" also holds entries: "mushroom A is safe to eat", "mushroom B is dangerous".

### Innate (the experience of generations)

- **A drive for food.** Slightly hungry: an almost full pull; just fed: a weak one. Stored food does not quench it (a wolf in a sheepfold).
- **The expectation from hunting**: as much as hunting yields in good times. The individual is a hunter: its memory of hunting never falls below 45 % of the innate value.
- **Sleep.** Pulls by fatigue, and more if the individual has not slept for long.

### How a way is chosen

The drive for food goes to **one** way at a time. Hunting is always open. Other ways open as hunting "is not working", that is, as its expectation falls below the innate one. Ways compete by their expectations. A business already begun holds on: while an attempt is under way, its pull is stronger the closer the ball is to its goal. A new decision (after sleep or after a catch) is made by expectations alone. All pushes (food, sleep) are added without an arbiter.

### Six ways to learn (there are no others in the program)

1. **The expectation of a way** is updated by hours of effort: a catch gives relief 1, water 1/6, nothing 0. Hours of sleep do not count.
2. **The length of memory.** While experience is small, each hour changes the expectation noticeably; with experience, less. But memory is not longer than about three days of effort: a week of complete failure undermines faith in a way.
3. **Return to hunting.** While the individual does not hunt, its expectation from hunting returns by itself to the innate value, in about a week. When hard times end, the individual tries hunting again and, if it feeds, returns to it.
4. **Birth of a new graph**, for two reasons: **agony** (at the edge of starvation, see below) and **novelty** (it saw a neighbour with mushrooms and has no graph "mushrooms" yet). A newborn graph inherits the innate expectation of hunting with a small random deviation.
5. **Entries in the matrix of graph "mushrooms".** Saw a neighbour poisoned by mushroom B: "B is dangerous"; saw a neighbour eat mushroom A and be fine: "A is safe". Ate one itself and survived: "this one is safe" (a false lesson is possible: surviving after B).
6. **Skill.** Each success on a risky way lowers its danger for this individual.

### Birth of a new graph in agony

While life is bearable there are no new ideas. A new graph is born only at the edge: the ball is close to Hunger (a threshold with noise), the body is hungry, nothing has been eaten for long, and neither old hunting nor a way that has worked before has helped. At the moment of birth comes **insight**: the ball at once finds itself close to the new vertex, and the new way is tried immediately. Closeness to Hunger brings a **surge of strength** (adrenaline): the push is stronger, but fatigue grows faster; the surge fades slowly, in about a day.

If the individual lacks the capacity to give rise to the new (for comparison), it can get a new graph only by novelty, by learning from the neighbour.

### An individual without memory (for comparison)

The same body and the same capacity to give rise to the new, but its graphs remember nothing: a fixed rule "old hunting -> a way that has worked before -> a new graph".

## 4. How the world is built

| | What it is | Numbers |
|---|---|---|
| Time | tick = hour, day = 24 ticks | lifespan limit 400 days |
| Hunger | grows by itself, falls only with food | without food the body lasts ~20 days |
| Hunting | the main way; a catch is 3 portions: one eaten at once, two stored | stored food spoils in ~10 days |
| Sleep | falls asleep when close to the Sleep vertex; a sleeping body does not move | no longer than 3 days awake, then sleep comes by force; sleep ~6 h (longer after sleeplessness, shorter on an empty stomach) |
| Hard times | hunting is 5 times harder | ~30 days once in ~100 days, 4 times in a life |
| Tree | feeds even in hard times | risk of falling 15 % per catch, less with skill |
| Water | does not feed; the body lives on its own reserves (loses weight) | each drink is ~2 days of life; risk of drowning 20 %, less with skill |
| Mushrooms | feed; good (A) and poisonous (B); mushrooms are scarce | a patch holds 2 meals, one grows back in ~3 weeks; mushroom B kills in 80 % of cases |
| Neighbour | a random meeting instead of a herd | about once in 15 days: sees the neighbour eat mushrooms, get poisoned, fall, drown, starve |

Which way the world offers at the birth of a new graph is decided by chance. Only the world knows the properties of the ways.

## 5. What is set in advance

**Calibration by the Agent**: quantities that in the living are set by the experience of generations and in the program are set by its author:

- the edge of agony: closeness to Hunger 0.4 (the program works within 0.35-0.45); body hunger above 0.4; no food for more than 60 h (and 120 h more if a way has worked before); at least 200 h between births;
- insight: the ball is moved 60 % of the way to the new vertex;
- surge of strength: starts at closeness to Hunger 0.3; the push up to twice as strong; fades in ~a day;
- the innate expectation of hunting; memory of hunting not below 45 %; memory horizon ~3 days; return of hunting ~a week; commitment to the business at hand;
- sleep: "not slept for long" is more than 36 h.

**The world** (section 4) is also set in advance and is the same in all experiments.

**Randomness.** The noise source is hardware randomness of the computer itself; every value is new, so two lives never repeat exactly. Noise is not a reaction to a tie between options but a permanent part of the program: in the executor (every hour), at the edge of agony, in which way is offered at a birth, in the expectation inherited by a newborn graph, in the length of sleep, in the risk of ways, in which mushroom is picked, in meetings with the neighbour. To debug a single part, the noise stream can be recorded and replayed; the result then matches bit for bit.

## 6. How to repeat

The code and instructions are on the author's website (a link to download). Each table and figure of chapter 32 comes from one command; the expected numbers match the book within the random spread between series (about ±10 %).
