# Causa Sui: the simulated world of chapter 32

This program lives the life of an individual in a simulated world, to test whether the
mechanisms described in *Causa Sui* (graphs, matrices, the capacity to give rise to the
new in agony) are consistent and what they change. It is the frozen reference version
used for every number and figure of chapter 32 of book 3. It is a model of the mechanisms,
not a subject (see chapter 31). A plain-language description of the algorithm is in
`docs/ALGORITHM_EN.md` (Russian: `docs/АЛГОРИТМ_RU.md`).

## Requirements
Python 3.11 or newer (tested with 3.13), numpy (tested 2.5), matplotlib (3.11, figures only),
scipy (1.18, optional: the Wilcoxon test). Graphviz `dot` only to redraw figure 32.0a.

    pip install numpy matplotlib scipy

## Files
| File | What it is |
|---|---|
| `world.py` | the simulated world and the individual's body; the world passport (`WorldParams`) |
| `individual.py` | graphs with memory, graphs without memory (comparison), birth of a graph in agony, executor |
| `main.py` | the main loop: one life, one tick = one hour |
| `signals.py`, `noise.py` | what passes between the parts; hardware noise source |
| `tests.py` | 18 control cases with a known answer |
| `experiments/` | the experiments and figures of chapter 32 |
| `data/` | the published series (lives of the individuals behind table 32.1 and figure 32.1) |
| `docs/` | the algorithm in plain words (EN, RU); sources of figures 32.0a, 32.0b |
| `figures/` | figures 32.0a-32.3, Russian and English, sized for an A5 page |

## Check the program
    python3 tests.py                  # 18 of 18 must pass
    python3 main.py                   # one life; journal in journal.txt

## Reproduce chapter 32 (run inside experiments/)
Every life uses fresh hardware noise, so numbers vary between series (about ±10 %);
the qualitative results do not.

| Chapter 32 | Command | Published values |
|---|---|---|
| Survival in the first-fourth hard times (table, fig. 32.1) | `python3 hard_times.py memory 100`; `... nomemory 100`; `... nobirth 100` (the published series of 200 are two runs of 100 merged) | finds its own and remembers (200): 60 / 86 / 88 / 88 %, lived out the full lifespan 52 of 200; does not remember (200): 29-38 / 0 %; only observation (100): 47 / 38 / 0 % |
| Figure 32.1 | `python3 figures.py survival ru` / `en` (reads `../data`, or your own `hard_times_*.json`) | |
| World calibration | `python3 birth_in_agony.py c1_good 100`; `c2_hard`; `c3_oracle` | good times 100/100 live to old age; hard times with nothing new 0/100 survive the first; oracle 77/100 survive the first, 37/100 live to old age |
| Birth in agony, stress | `python3 birth_in_agony.py full 100`; `insight`; `adrenaline`; `nostress`; `nobirth` | survived first / lived out the lifespan: 59/20, 61/22, 56/14, 57/8, 48/0 |
| Experience or selection | `python3 experience_vs_selection.py 90` | peak hunger, same individuals: first 0.74, second 0.25 (medians), lower in 24 of 33, Wilcoxon p ~ 7e-5 |
| Figures 32.0a, 32.0b | `cd ../docs; dot -Tpng -Gdpi=300 structure_en.dot -o fig32_0a_structure_en.png`; `python3 simplex_fig.py en` | |
| Figures 32.2, 32.3 (illustrations) | `python3 figures.py life ru`; `python3 figures.py lostlife ru` (then `en`: the same life is reused) | chosen from several lives |

The figure scripts save their PNG files in the current folder; move them to `figures/` to replace the published ones.

Percentages for each hard-time period are of the individuals **alive at its start**,
not of the initial hundred (e.g. 86 % in the second hard times is 79 of 92).

## Randomness
Noise comes from the operating system's hardware entropy (`os.urandom`). A whole life
cannot be repeated exactly; a single part can be: record its noise stream
(`NoiseSource("hw", record=True)`) and replay it (`NoiseSource("replay", replay=...)`).

## Integrity
`SHA256SUMS` lists the checksum of every file: `sha256sum -c SHA256SUMS`.

## Provenance
Frozen reference version "3k" (world v6, graphs v6), 3-4 October 2026. This English
edition was checked against the original: with the same recorded noise streams the two
programs produce bit-identical lives.
