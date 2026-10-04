"""Figures for chapter 32, in Russian or English, sized for an A5 page (~12 cm wide).

  python3 figures.py survival  <ru|en> [data_dir]   -> fig32_1_survival_<lang>.png
  python3 figures.py life      <ru|en> [tries]      -> fig32_2_life_<lang>.png (survives all hard times)
  python3 figures.py lostlife  <ru|en> [tries]      -> fig32_3_life_lost_<lang>.png (dies in the first)
The chosen life is saved (../data/life_survivor.json, life_lost.json) and reused, so the
Russian and English figures show the same life.

Figure 32.1 reads hard_times_{nobirth,nomemory,memory}.json (made by hard_times.py; the
published series are in ../data). Figures 32.2-32.3 run new lives until one fits the
description; they are illustrations, chosen from several lives (noise is hardware noise).
"""
from __future__ import annotations
import os
import sys
import json
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

from common import LIMIT, hard_periods, survival_by_period
import main

CM = 1 / 2.54
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
                     "legend.fontsize": 7.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
                     "font.family": "DejaVu Sans"})
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
WAY_COLOR = {"hunting": "#2a78d6", "mushrooms": "#eda100", "tree": "#1baf7a", "water": "#8a8a8a"}
INK, MUTED, BAND = "#1f1f1e", "#6b6a64", "#e6e5df"

TEXT = {
    "ru": dict(
        title1="Сколько индивидов пережили трудные времена",
        periods=["Первые", "Вторые", "Третьи", "Четвёртые"], periods_suffix="трудные\nвремена",
        y1="пережили, % от доживших до их начала",
        nobirth="Только подсмотренное (своё найти не может)",
        nomemory="Находит своё, но не помнит",
        memory="Находит своё и помнит",
        note1="Под столбцами: пережили / дожили до начала. «—»: до этих времён не дожил никто.",
        hunger="голод", day="дни", feeds="чем кормится",
        ways={"hunting": "охота", "mushrooms": "грибы", "tree": "дерево", "water": "вода (не кормит)"},
        hard="трудные времена", bands="серые полосы — трудные времена",
        born_novelty="увидел соседа с грибами", born_agony={"tree": "придумал залезть на дерево",
                                                           "water": "придумал пить воду",
                                                           "mushrooms": "придумал есть грибы"},
        title2="Одна жизнь: голод и чем индивид кормится",
        title3="Жизнь, оборвавшаяся в первые трудные времена",
        death={"drowned": "утонул", "fell from a tree": "упал с дерева", "poisoned": "отравился",
               "starvation": "умер от голода"},
    ),
    "en": dict(
        title1="How many individuals survived hard times",
        periods=["First", "Second", "Third", "Fourth"], periods_suffix="hard\ntimes",
        y1="survived, % of those alive at their start",
        nobirth="Only what is learned by observation (cannot find its own)",
        nomemory="Finds its own but does not remember",
        memory="Finds its own and remembers",
        note1="Under the bars: survived / alive at the start. —: nobody lived to these times.",
        hunger="hunger", day="days", feeds="what feeds it",
        ways={"hunting": "hunting", "mushrooms": "mushrooms", "tree": "tree", "water": "water (does not feed)"},
        hard="hard times", bands="grey bands — hard times",
        born_novelty="saw a neighbour with mushrooms", born_agony={"tree": "came up with climbing a tree",
                                                                 "water": "came up with drinking water",
                                                                 "mushrooms": "came up with eating mushrooms"},
        title2="One life: hunger and what feeds the individual",
        title3="A life cut short in the first hard times",
        death={"drowned": "drowned", "fell from a tree": "fell from a tree", "poisoned": "poisoned",
               "starvation": "starved"},
    ),
}


def fig_survival(lang: str, data_dir: str):
    T = TEXT[lang]
    series = [("nobirth", BLUE), ("nomemory", ORANGE), ("memory", GREEN)]
    fig, ax = plt.subplots(figsize=(12 * CM, 8.5 * CM), dpi=300)
    w, x = 0.26, np.arange(4)
    for i, (key, col) in enumerate(series):
        runs = json.load(open(os.path.join(data_dir, f"hard_times_{key}.json")))
        rows = survival_by_period(runs)
        for k, (e, s) in enumerate(rows):
            xx = x[k] + (i - 1) * w
            if e == 0:
                ax.text(xx, 1.5, "—", ha="center", va="bottom", color=MUTED, fontsize=7)
                continue
            v = 100 * s / e
            ax.bar(xx, v, w - 0.03, color=col, label=T[key] if k == 0 else None)
            ax.text(xx, v + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=6.5, color=INK)
            ax.text(xx, -3 - 5 * (i % 2), f"{s}/{e}", ha="center", va="top", fontsize=5.2, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{p}\n{T['periods_suffix']}" for p in T["periods"]])
    ax.tick_params(axis="x", pad=19, length=0)
    ax.set_ylim(0, 112)
    ax.set_ylabel(T["y1"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.yaxis.grid(True, color=BAND)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", fontsize=6.5)
    ax.set_title(T["title1"], color=INK)
    fig.text(0.01, 0.01, T["note1"], fontsize=5.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = f"fig32_1_survival_{lang}.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def live():
    """One life with the daily record needed for the simplified portrait."""
    s = main.Simulation()
    days = LIMIT // 24 + 1
    hunger = np.full(days, np.nan)
    fed = [set() for _ in range(days)]
    marks = []
    with ThreadPoolExecutor(len(s.parallel)) as pool:
        while s.world.alive and s.tick < LIMIT:
            n_lines = len(s.log.lines)
            s.step(pool)
            h = s.history[-1]
            d = h["tick"] // 24
            hunger[d] = h["hunger"] if np.isnan(hunger[d]) else max(hunger[d], h["hunger"])
            for e in h["events"]:
                if e.startswith("catch: "):
                    fed[d].add(e.split(": ", 1)[1])
                elif e.startswith("drank"):
                    fed[d].add("water")
            for line in s.log.lines[n_lines:]:
                if "GRAPH BIRTH" in line:
                    name = re.search(r"GRAPH BIRTH '([^']+)'", line).group(1)
                    marks.append((h["tick"] / 24, name, "novelty" in line))
    return s, hunger[:s.tick // 24 + 1], fed[:s.tick // 24 + 1], marks


def find_life(survivor: bool, tries: int, path: str):
    """Run lives until one fits; save its daily record to `path` (both languages draw the same life)."""
    per = hard_periods()
    for _ in range(tries):
        s, hunger, fed, marks = live()
        agony = [m for m in marks if not m[2]]
        if survivor and s.world.death_cause == "old age" and agony:
            break
        if not survivor and per[0][0] < s.tick <= per[0][1] + 24 and s.world.death_cause != "old age":
            break
    else:
        raise SystemExit("no suitable life found; increase tries")
    rec = dict(hunger=[None if np.isnan(h) else float(h) for h in hunger], fed=[sorted(f) for f in fed],
               marks=marks, cause=s.world.death_cause)
    with open(path, "w") as f:
        json.dump(rec, f)
    return rec


def fig_life(lang: str, survivor: bool, rec: dict):
    T = TEXT[lang]
    per = hard_periods()
    hunger = np.array([np.nan if h is None else h for h in rec["hunger"]])
    fed = [set(f) for f in rec["fed"]]
    marks = rec["marks"]
    days = np.arange(len(hunger))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12 * CM, 7.5 * CM), dpi=300, sharex=True,
                                 gridspec_kw=dict(height_ratios=[3, 1.2]))
    for a in (a1, a2):
        for b0, b1 in per:
            if b0 / 24 < len(days):
                a.axvspan(b0 / 24, min(b1 / 24, len(days)), color=BAND, lw=0)
        for s_ in ("top", "right"):
            a.spines[s_].set_visible(False)
    a1.plot(days, hunger, color=INK, lw=1)
    a1.set_ylim(0, 1.05)
    a1.set_ylabel(T["hunger"])
    keys = []
    for i, (t, name, novelty) in enumerate(sorted(marks), 1):
        label = T["born_novelty"] if novelty else T["born_agony"].get(name, name)
        y = hunger[min(int(t), len(hunger) - 1)]
        a1.plot(t, y, "o", ms=7.5, mfc="white", mec=INK, mew=0.8, zorder=5)
        a1.text(t, y, str(i), ha="center", va="center", fontsize=5.5, zorder=6)
        keys.append(f"{i} — {label}")
    if rec["cause"] != "old age":
        a1.plot(len(days) - 1, hunger[-1], "x", color=INK, ms=5)
        a1.text(len(days) - 1, hunger[-1] - 0.12, T["death"].get(rec["cause"], rec["cause"]), fontsize=6, ha="center")
    used = [w for w in ("hunting", "mushrooms", "tree", "water") if any(w in f for f in fed)]
    for row, wname in enumerate(used):
        xs = [d for d in days if wname in fed[d]]
        a2.scatter(xs, [row] * len(xs), marker="|", s=18, color=WAY_COLOR[wname], lw=1)
    a2.set_yticks(range(len(used)))
    a2.set_yticklabels([T["ways"][w] for w in used])
    a2.set_ylim(-0.7, len(used) - 0.3)
    a2.set_xlabel(T["day"])
    a2.set_title(T["feeds"], fontsize=7, loc="left", color=MUTED)
    a1.set_title(T["title2"] if survivor else T["title3"], color=INK)
    keys.append(T["bands"])
    fig.text(0.01, 0.01, ";   ".join(keys), fontsize=5.5, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out = f"fig32_{'2_life' if survivor else '3_life_lost'}_{lang}.png"
    fig.savefig(out)
    plt.close(fig)
    return out


if __name__ == "__main__":
    what = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "ru"
    if what == "survival":
        data = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), "..", "data")
        print(fig_survival(lang, data))
    else:
        survivor = what == "life"
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data",
                            f"life_{'survivor' if survivor else 'lost'}.json")
        if os.path.exists(path):
            rec = json.load(open(path))
        else:
            rec = find_life(survivor, int(sys.argv[3]) if len(sys.argv) > 3 else 20, path)
        print(fig_life(lang, survivor, rec))
