"""Figure A.2: the individual's choice as a ball in a triangle (RU/EN)."""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = {"ru": dict(H="Голод\nкасание — смерть", O="Охота\nкасание — добыча", S="Сон\nблизость — засыпает",
                ball="выбор\n(шарик)", pH="тяга голода\n(растёт с голодом)", pO="порыв к еде",
                pS="усталость",
                note="Рождённые графы (грибы, дерево, вода) добавляют новые вершины:\nтреугольник становится многогранником."),
     "en": dict(H="Hunger\ntouch = death", O="Hunting\ntouch = catch", S="Sleep\nclose = falls asleep",
                ball="choice\n(ball)", pH="pull of hunger\n(grows with hunger)", pO="drive for food",
                pS="fatigue",
                note="Born graphs (mushrooms, tree, water) add new vertices:\nthe triangle becomes a polytope.")}
lang = sys.argv[1]
t = T[lang]
V = {"H": np.array([-0.2, -0.1]), "O": np.array([1.2, -0.1]), "S": np.array([0.5, 1.112])}
fig, ax = plt.subplots(figsize=(12 / 2.54, 9 / 2.54), dpi=300)
tri = np.array([V["H"], V["O"], V["S"], V["H"]])
ax.fill(tri[:, 0], tri[:, 1], color="#f3f4f2", ec="#6b6a64", lw=1)
ball = 0.34 * V["H"] + 0.34 * V["O"] + 0.32 * V["S"]
for k, col, lab, ha, off in (("H", "#c0392b", t["pH"], "center", (-0.1, -0.13)),
                             ("O", "#2a78d6", t["pO"], "center", (0.08, -0.09)),
                             ("S", "#6b6a64", t["pS"], "left", (0.03, 0.0))):
    d = V[k] - ball
    tip = ball + 0.24 * d / np.linalg.norm(d)
    ax.annotate("", xy=tip, xytext=ball, arrowprops=dict(arrowstyle="-|>", color=col, lw=1.2))
    ax.text(*(tip + np.array(off)), lab, fontsize=6.5, color=col, ha=ha, va="center")
ax.plot(*ball, "o", ms=9, color="#1f1f1e", zorder=5)
ax.text(ball[0] + 0.05, ball[1] + 0.05, t["ball"], fontsize=6.5, ha="left")
ax.text(-0.2, -0.16, t["H"], ha="center", va="top", fontsize=7.5)
ax.text(1.2, -0.16, t["O"], ha="center", va="top", fontsize=7.5)
ax.text(0.5, 1.15, t["S"], ha="center", va="bottom", fontsize=7.5)
ax.text(0.5, -0.42, t["note"], ha="center", va="top", fontsize=6.5, color="#6b6a64")
ax.set_xlim(-0.45, 1.45); ax.set_ylim(-0.62, 1.32); ax.set_aspect("equal"); ax.axis("off")
fig.tight_layout(); fig.savefig(f"fig32_0b_choice_{lang}.png")
