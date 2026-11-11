"""layout.json + CSV -> ../자취방_평면도.pdf (2쪽) / 자취방_평면도.png / 자취방_공기흐름도.png  (A4 세로)"""
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, Arc, Polygon, FancyArrowPatch
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
L = json.loads((HERE / "layout.json").read_text(encoding="utf-8"))

for f in ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"):
    if Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

R, K, WBY, I = L["room"], L["kitchen"], L["wardrobeBay"], L["items"]
W, D, H, T = R["w"], R["d"], R["h"], R["wallT"]
win, bd, ent, S = L["window"], L["bathDoor"], L["entrance"], L["sensor"]

INK, POCHE, FUR, FILL, DIM, SIG = "#1f2328", "#3a3f45", "#4a4f55", "#f4f3ef", "#2d5277", "#d4502a"
C_IN, C_OUT, C_PL, C_CO = "#2f7fd0", "#e0572a", "#d99a2b", "#4fb0c6"
MUTED = "#646b72"
PAGE_W, PAGE_H, MM = 210, 297, 1 / 25.4

# ---------------- data analysis (same method as the 3D page) ----------------
rows = list(csv.reader((OUT.parent / "Co2 측정.csv").open(encoding="cp949")))[3:]
co2 = [int(float(r[2])) for r in rows if len(r) > 2 and r[2].strip()]
N = len(co2); CO = L["outdoorCO2"]
ip = co2.index(max(co2)); i0 = min(range(0, 40), key=lambda i: co2[i])
xs = [(i - ip) / 60 for i in range(ip + 5, N)]; ys = [math.log(co2[i] - CO) for i in range(ip + 5, N)]
mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
a0 = my - b * mx
r2 = 1 - sum((y - (a0 + b * x)) ** 2 for x, y in zip(xs, ys)) / sum((y - my) ** 2 for y in ys)
n_ach = -b


def poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


wd = I["wardrobe"]
AREA = poly_area(L["floor"]) - (wd["x1"] - wd["x0"]) * (wd["z1"] - wd["z0"])
VOL = AREA * H
gen = [VOL * ((co2[i + 3] - co2[i - 3]) / 6 * 60 * 1e-6 + n_ach * (co2[i] - CO) * 1e-6) for i in range(i0 + 5, ip - 3)]
GEN = sum(gen) / len(gen)


# ---------------- base plan drawing ----------------
def make_plan_axes(fig, left_mm, top_mm, scale, x0, x1, z0, z1):
    w = (x1 - x0) * 1000 / scale; h = (z1 - z0) * 1000 / scale
    ax = fig.add_axes([left_mm / PAGE_W, 1 - (top_mm + h) / PAGE_H, w / PAGE_W, h / PAGE_H])
    ax.set_xlim(x0, x1); ax.set_ylim(-z1, -z0); ax.set_aspect("equal"); ax.axis("off")
    return ax, w, h


def draw_plan(ax, faint=False, labels=True, dims=True, sensor=True):
    a = 0.45 if faint else 1.0
    fur = "#9aa0a6" if faint else FUR
    P = lambda x, z: (x, -z)

    def rect(x0, x1, z0, z1, fc=FILL, ec=None, lw=0.6, ls="-", z=2, hatch=None, alpha=1):
        ax.add_patch(Rectangle((x0, -z1), x1 - x0, z1 - z0, fc=fc, ec=ec or fur, lw=lw, ls=ls, zorder=z, hatch=hatch, alpha=alpha))

    def text(x, z, s, size=6.2, color=INK, weight="normal", ha="center", va="center", **kw):
        if not labels:
            return
        ax.text(x, -z, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, zorder=6, **kw)

    ax.add_patch(Polygon([P(*p) for p in L["floor"]], closed=True, fc="#fbfaf7", ec="none", zorder=0))
    # walls
    for wl in L["walls"]:
        axis, at, inward, span = wl["axis"], wl["at"], wl["inward"], wl["span"]
        t0, t1 = (at - T, at) if inward > 0 else (at, at + T)
        cur = span[0]
        segs = []
        for o in sorted(wl.get("open", []), key=lambda o: o["a0"]):
            segs.append((cur, o["a0"])); cur = o["a1"]
        segs.append((cur, span[1]))
        for s0, s1 in segs:
            if s1 - s0 < 1e-3:
                continue
            if axis == "x":
                rect(s0, s1, t0, t1, fc=POCHE, ec=POCHE, lw=0.4, z=3, alpha=a)
            else:
                rect(t0, t1, s0, s1, fc=POCHE, ec=POCHE, lw=0.4, z=3, alpha=a)
    # window (closed sliding sashes)
    rect(win["x0"], win["x1"], -T, 0, fc="white", ec=INK, lw=0.6, z=4, alpha=a)
    mid = (win["x0"] + win["x1"]) / 2
    ax.plot([win["x0"], mid + 0.05], [0.03, 0.03], color=INK, lw=0.8, zorder=5, alpha=a)
    ax.plot([mid - 0.05, win["x1"]], [0.065, 0.065], color=INK, lw=0.8, zorder=5, alpha=a)
    ax.plot([win["x0"], win["x1"]], [0.1, 0.1], color=INK, lw=0.4, zorder=5, alpha=a)
    # doors (closed leaf + swing line)
    def door(hinge, leaf_dir, close_dir, width):
        hx, hz = hinge
        ex, ez = hx + close_dir[0] * width, hz + close_dir[1] * width
        ax.plot([hx, ex], [-hz, -ez], color=INK, lw=1.2, zorder=5, alpha=a)
        a1 = math.degrees(math.atan2(-leaf_dir[1], leaf_dir[0])); a2 = math.degrees(math.atan2(-close_dir[1], close_dir[0]))
        lo, hi = sorted([a1, a2])
        if hi - lo > 180:
            lo, hi = hi, lo + 360
        ax.add_patch(Arc((hx, -hz), 2 * width, 2 * width, theta1=lo, theta2=hi, color=INK, lw=0.4, ls=(0, (3, 2)), zorder=5, alpha=a * 0.8))
    door((-T / 2, bd["z0"]), (-1, 0), (0, 1), bd["z1"] - bd["z0"])
    door((ent["x0"], D + T / 2), (0, 1), (1, 0), ent["x1"] - ent["x0"])
    text(-0.55, (bd["z0"] + bd["z1"]) / 2, "화장실", size=6.4, color=fur)
    text((ent["x0"] + ent["x1"]) / 2, D + T + 0.55, "현관문 (복도)", size=6, color=fur)
    text(mid, -T - 0.2 if not dims else -T - 0.17, "창문 (닫힘)", size=5.8, color=fur)

    # furniture
    it = I["rug"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="#f1f1ef", ec="#b5b9bd", lw=0.4, ls=(0, (2, 1.5)), z=1)
    it = I["bathMat"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="#f4efe4", ec="#b5b9bd", lw=0.4, z=1)
    it = I["bed"]; rect(it["x0"], it["x1"], it["z0"], it["z1"])
    cxb = (it["x0"] + it["x1"]) / 2
    for k, (pw, pd) in enumerate([(0.92, 0.34), (0.62, 0.38), (0.52, 0.33), (0.42, 0.28)]):
        rect(cxb - pw / 2, cxb + pw / 2, it["z0"] + 0.07, it["z0"] + 0.07 + pd, fc="white", lw=0.35, z=3 + k * 0.01)
    ax.plot([it["x0"], it["x1"]], [-(it["z0"] + 0.62), -(it["z0"] + 0.95)], color=fur, lw=0.4, zorder=3)
    text(cxb, (it["z0"] + it["z1"]) / 2 + 0.35, "침대")
    for k in ("bookshelf", "drawer", "cabinet", "desk"):
        it = I[k]; rect(it["x0"], it["x1"], it["z0"], it["z1"])
    it = I["bookshelf"]; ax.plot([it["x0"], it["x1"]], [-(it["z0"] + 0.15)] * 2, color=fur, lw=0.3, zorder=3)
    text((it["x0"] + it["x1"]) / 2, it["z1"] + 0.11, "책장", size=6)
    it = I["drawer"]; text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2, "서랍장", size=5.2)
    it = I["cabinet"]; text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2, "신발장", size=5.4)
    it = I["desk"]; text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2 + 0.05, "책상", size=6)
    it = I["tallShelf"]; rect(it["x0"], it["x1"], it["z0"], it["z1"])
    ax.plot([it["x0"], it["x1"]], [-it["z0"], -it["z1"]], color="#b5b9bd", lw=0.35, zorder=3)
    text((it["x0"] + it["x1"]) / 2, it["z0"] - 0.1, "선반", size=5.4)
    it = I["mat"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="#ecebe7"); text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2, "접이식 매트", size=5.8)
    it = I["lamp"]; ax.add_patch(Circle(P((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2), 0.1, fc=FILL, ec=fur, lw=0.5, zorder=3))
    it = I["rack"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="white")
    ax.plot([it["x0"], it["x1"]], [-it["z0"], -it["z1"]], color="#b5b9bd", lw=0.4, zorder=3)
    ax.plot([it["x0"], it["x1"]], [-it["z1"], -it["z0"]], color="#b5b9bd", lw=0.4, zorder=3)
    it = I["fridge"]; rect(it["x0"], it["x1"], it["z0"], it["z1"]); text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2, "냉장고", size=5.8)
    it = I["dehum"]
    ax.add_patch(FancyBboxPatch((it["x0"] + 0.04, -it["z1"] + 0.04), it["x1"] - it["x0"] - 0.08, it["z1"] - it["z0"] - 0.08, boxstyle="round,pad=0.04", fc=FILL, ec=fur, lw=0.6, zorder=3))
    text((it["x0"] + it["x1"]) / 2, it["z0"] - 0.1, "제습기", size=5.2)
    it = I["chair"]; ax.add_patch(Circle(P((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2), 0.24, fc=FILL, ec=fur, lw=0.5, zorder=3))
    rect(it["x0"] + 0.05, it["x1"] - 0.05, it["z0"] - 0.02, it["z0"] + 0.06, fc="#e4e3df", z=4)
    text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2 + 0.03, "의자", size=5.4)
    it = I["shoeArea"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="#efe9e3", lw=0.5, z=1, hatch="++++" if not faint else None)
    text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2, "현관", size=6, bbox=dict(fc="white", ec="none", pad=0.6))
    it = I["wardrobe"]; rect(it["x0"], it["x1"], it["z0"], it["z1"])
    ax.plot([it["x0"] + 0.2] * 2, [-(it["z0"] + 0.06), -(it["z1"] - 0.06)], color=fur, lw=0.4, zorder=3)
    for zz in [it["z0"] + 0.12 + k * 0.09 for k in range(10)]:
        ax.plot([it["x0"] + 0.13, it["x0"] + 0.27], [-(zz - 0.04), -(zz + 0.04)], color="#b5b9bd", lw=0.35, zorder=3)
    text(it["x0"] + 0.43, (it["z0"] + it["z1"]) / 2, "붙박이장", size=5.6, rotation=90)
    it = I["sink"]
    rect(K["x0"], it["x1"], K["z0"], K["z1"], fc="#efefec")
    ax.add_patch(FancyBboxPatch((K["x0"] + 0.12, -(it["z1"] - 0.08)), 0.34, it["z1"] - it["z0"] - 0.18, boxstyle="round,pad=0.02", fc="white", ec=fur, lw=0.5, zorder=3))
    text(K["x0"] + 0.29, (it["z0"] + it["z1"]) / 2 - 0.02, "싱크", size=5.4)
    it = I["washer"]; ax.add_patch(Circle(P((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2), 0.2, fc="white", ec=fur, lw=0.5, zorder=3))
    text((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2, "세탁기", size=5.2)
    it = I["upperCab"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="none", lw=0.45, ls=(0, (3, 2)), z=4)
    it = I["basket"]; ax.add_patch(Circle(P((it["x0"] + it["x1"]) / 2, (it["z0"] + it["z1"]) / 2), 0.16, fc=FILL, ec=fur, lw=0.5, zorder=3))
    it = I["bin"]; rect(it["x0"], it["x1"], it["z0"], it["z1"])
    it = I["ac"]; rect(it["x0"], it["x1"], it["z0"], it["z1"], fc="none", lw=0.5, ls=(0, (3, 2)), z=4)
    text(it["x0"] - 0.06, (it["z0"] + it["z1"]) / 2 + 0.38, "에어컨(벽걸이)", size=5.2, ha="right", color=fur)
    if sensor:
        sx, sz = S["x"], S["z"]
        ax.add_patch(Circle(P(sx, sz), 0.12, fc="none", ec=SIG, lw=0.7, zorder=7))
        ax.add_patch(Circle(P(sx, sz), 0.055, fc=SIG, ec="white", lw=0.5, zorder=8))
    return P


# ---------------- dimensions ----------------
def dim(ax, a, b, off, label, tick=0.05, size=6.2, bold=False):
    (ax_, az_), (bx_, bz_) = a, b
    ox, oz = off
    pa, pb = (ax_ + ox, az_ + oz), (bx_ + ox, bz_ + oz)
    ax.plot([pa[0], pb[0]], [-pa[1], -pb[1]], color=DIM, lw=0.45, zorder=6)
    for (px, pz), (qx, qz) in ((a, pa), (b, pb)):
        ax.plot([px + ox * 0.12, qx + ox * 0.15], [-(pz + oz * 0.12), -(qz + oz * 0.15)], color=DIM, lw=0.3, zorder=6)
        ax.plot([qx - tick, qx + tick], [-(qz - tick), -(qz + tick)], color=DIM, lw=0.8, zorder=6)
    mxx, mzz = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
    rot = 90 if abs(bx_ - ax_) < 1e-6 else 0
    ax.text(mxx + (-0.07 if rot else 0), -mzz + (0 if rot else 0.06), label, fontsize=size, color=DIM, rotation=rot,
            ha="center", va="bottom" if not rot else "center", zorder=6, fontweight="bold" if bold else "normal")


mm = lambda v: f"{round(v * 1000):,}"


def header(fig, left, title, sub, right):
    fig.text(left / PAGE_W, 1 - 13 / PAGE_H, title, fontsize=13, fontweight="bold", color=INK, va="baseline")
    fig.text(left / PAGE_W, 1 - 19 / PAGE_H, sub, fontsize=7.5, color=MUTED, va="baseline")
    fig.text((PAGE_W - left) / PAGE_W, 1 - 13 / PAGE_H, right, fontsize=9, color=INK, ha="right", va="baseline", fontweight="bold")


def title_block(fig, left, width, top, rows):
    tb_h = 24
    tb = fig.add_axes([left / PAGE_W, 1 - (top + tb_h) / PAGE_H, width / PAGE_W, tb_h / PAGE_H]); tb.axis("off")
    tb.set_xlim(0, width); tb.set_ylim(0, tb_h)
    tb.add_patch(Rectangle((0, 0), width, tb_h, fc="none", ec=INK, lw=0.9))
    cols = [0, 0.30, 0.62, 0.80, 1.0]
    for c in cols[1:-1]:
        tb.plot([c * width] * 2, [0, tb_h], color=INK, lw=0.5)
    tb.plot([0, width], [tb_h / 2] * 2, color=INK, lw=0.5)
    for r_, row in enumerate(rows):
        y = tb_h - r_ * tb_h / 2
        for c_ in range(4):
            x = cols[c_] * width
            tb.text(x + 1.6, y - 2.2, row[c_ * 2], fontsize=5.2, color=MUTED, va="top")
            tb.text(x + 1.6, y - 6.0, row[c_ * 2 + 1], fontsize=6.6, color=INK, va="top", fontweight="bold" if (r_ == 1 and c_ == 0) else "normal")


def ftext(fig, xmm, ymm, s, **kw):
    fig.text(xmm / PAGE_W, 1 - ymm / PAGE_H, s, **kw)


# =============== PAGE 1: floor plan 1/40 ===============
fig1 = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
X0, X1, Z0, Z1 = -2.05, 3.65, -1.05, 6.35
plan_w = (X1 - X0) * 1000 / 40
left = (PAGE_W - plan_w) / 2
ax, pw, ph = make_plan_axes(fig1, left, 25, 40, X0, X1, Z0, Z1)
P = draw_plan(ax)
# sensor callout
sx, sz = S["x"], S["z"]
tx, tz = 0.62, 2.48
ax.annotate("", xy=P(sx - 0.12, sz + 0.02), xytext=P(tx + 1.0, tz - 0.05), arrowprops=dict(arrowstyle="-", color=SIG, lw=0.7), zorder=8)
ax.text(tx, -tz, f"{S['name']} ({S['model']})\n전자레인지 선반 위에서 두 번째 칸\n전기포트 옆 · 바닥 위 약 {S['y']:.2f} m",
        fontsize=6.0, color=SIG, ha="left", va="center", zorder=8, linespacing=1.45, bbox=dict(boxstyle="round,pad=0.45", fc="white", ec=SIG, lw=0.7))
ax.text(0.95, -3.45, "원룸 (침실 겸 거실)", fontsize=8.5, fontweight="bold", ha="center", color=INK, zorder=6)
ax.text(0.95, -3.72, f"바닥 {AREA:.1f} m² · 천장고 {H * 1000:,.0f}\n체적 약 {VOL:.1f} m³", fontsize=6.3, ha="center", va="center", color=FUR, linespacing=1.5, zorder=6)
ax.text(K["x0"] - T - 0.1, -(K["z0"] + K["z1"]) / 2, f"주방\n(깊이 {mm(-K['x0'])})", fontsize=6.2, ha="right", va="center", color=FUR, fontweight="bold")
# dims (bold = measured)
dim(ax, (0, -T), (win["x0"], -T), (0, -0.42), mm(win["x0"]), size=5.4)
dim(ax, (win["x0"], -T), (win["x1"], -T), (0, -0.42), mm(win["x1"] - win["x0"]))
dim(ax, (win["x1"], -T), (W, -T), (0, -0.42), mm(W - win["x1"]))
dim(ax, (0, -T), (W, -T), (0, -0.8), mm(W), bold=True)
dim(ax, (W + T, 0), (W + T, D), (0.55, 0), mm(D), bold=True)
dim(ax, (-T, 0), (-T, K["z0"]), (K["x0"] - 0.55, 0), mm(K["z0"]))
dim(ax, (K["x0"] - T, K["z0"]), (K["x0"] - T, K["z1"]), (-0.55, 0), mm(K["z1"] - K["z0"]), bold=True)
dim(ax, (K["x0"] - T, K["z1"]), (K["x0"] - T, D), (-0.55, 0), mm(D - K["z1"]))
dim(ax, (WBY["x0"], D + T), (0, D + T), (0, 0.42), mm(-WBY["x0"]))
dim(ax, (ent["x0"], D + T), (ent["x1"], D + T), (0, 0.42), mm(ent["x1"] - ent["x0"]))
dim(ax, (ent["x1"], D + T), (W, D + T), (0, 0.42), mm(W - ent["x1"]))
dim(ax, (WBY["x0"], D + T), (W, D + T), (0, 0.85), mm(W - WBY["x0"]))
header(fig1, left, "10주차 실내 CO₂ 측정 공간 평면도", "자취방 원룸 · 측정기 위치 표시 · 단위 mm · 굵은 치수는 실측", "S = 1/40")
# scale bar
sb_y = 25 + ph + 4
sb = fig1.add_axes([(left - 2) / PAGE_W, 1 - (sb_y + 5) / PAGE_H, 79 / PAGE_W, 5 / PAGE_H]); sb.axis("off")
sb.set_xlim(-2, 77); sb.set_ylim(0, 5)
for k in range(3):
    sb.add_patch(Rectangle((k * 25, 3.4), 25, 1.0, fc=INK if k % 2 == 0 else "white", ec=INK, lw=0.5))
for k in range(4):
    sb.text(k * 25, 2.6, f"{k} m", fontsize=6, ha="center", va="top", color=INK)
lg_top = sb_y + 10
ftext(fig1, left, lg_top, "범례", fontsize=7.5, fontweight="bold", color=INK, va="top")
lax = fig1.add_axes([left / PAGE_W, 1 - (lg_top + 26) / PAGE_H, 60 / PAGE_W, 22 / PAGE_H]); lax.axis("off")
lax.set_xlim(0, 60); lax.set_ylim(0, 22)
lax.add_patch(Circle((3, 18), 1.6, fc="none", ec=SIG, lw=0.7)); lax.add_patch(Circle((3, 18), 0.8, fc=SIG, ec="white", lw=0.4))
lax.text(8, 18, "CO₂ 측정기 위치 (H 약 0.65 m)", fontsize=6.4, va="center", color=INK)
lax.add_patch(Rectangle((0.8, 11), 4.4, 2.2, fc=POCHE, ec=POCHE)); lax.text(8, 12.1, "벽체", fontsize=6.4, va="center", color=INK)
lax.add_patch(Rectangle((0.8, 5), 4.4, 2.6, fc="none", ec=FUR, lw=0.5, ls=(0, (2, 1.5)))); lax.text(8, 6.3, "벽걸이·상부 설치물 (에어컨, 상부장)", fontsize=6.4, va="center", color=INK)
lax.plot([0.8, 5.2], [0.8, 0.8], color=FUR, lw=0.5); lax.text(8, 0.8, "가구 (바닥 설치)", fontsize=6.4, va="center", color=INK)
cx_ = left + 82
ftext(fig1, cx_, lg_top, "측정 조건", fontsize=7.5, fontweight="bold", color=INK, va="top")
conds = [
    ("측정일", "2026.11.11  18:14 – 21:16 (1분 간격)"),
    ("재실", "20대 남성 3명, 약 1시간 머문 뒤 퇴실"),
    ("개구부", "창문·현관문·화장실 문 모두 닫음"),
    ("측정기", f"{S['model']} · 선반 위에서 두 번째 칸, H 약 {S['y']:.2f} m"),
    ("실 체적", f"약 {VOL:.1f} m³ (바닥 {AREA:.1f} m² × 천장고 {H:.2f} m)"),
]
for k, (a_, b_) in enumerate(conds):
    ftext(fig1, cx_, lg_top + 5.5 + k * 4.6, a_, fontsize=6.4, color=MUTED, va="top")
    ftext(fig1, cx_ + 13, lg_top + 5.5 + k * 4.6, b_, fontsize=6.4, color=INK, va="top")
title_block(fig1, left, plan_w, 264, [
    ("과목", "환경설비실험", "실험", "실내 CO₂ 농도 측정 (10주차)", "축척", "1/40 (A4)", "단위", "mm"),
    ("도면", "측정 공간 평면도", "비고", "가로·세로·천장고·주방 폭 실측, 그 외 추정", "작성일", "2026.11.11", "도면번호", "A-01"),
])

# =============== PAGE 2: airflow (plan arrows + section A-A') ===============
fig2 = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
X0b, X1b, Z0b, Z1b = -1.35, 3.25, -0.9, 6.0
ax2, pw2, ph2 = make_plan_axes(fig2, 14, 26, 60, X0b, X1b, Z0b, Z1b)
P2 = draw_plan(ax2, faint=True, labels=False, dims=False, sensor=True)


def flow_arrow(ax, pts, color, lw=1.4, ms=7, section=False):
    vs = [(x, -z) for x, z in pts] if not section else pts
    codes = [MPath.MOVETO] + [MPath.CURVE3] * (len(vs) - 1) if len(vs) == 3 else [MPath.MOVETO] + [MPath.LINETO] * (len(vs) - 1)
    ax.add_patch(FancyArrowPatch(path=MPath(vs, codes), arrowstyle=f"-|>,head_length={ms * 0.06},head_width={ms * 0.035}", color=color, lw=lw, zorder=9, mutation_scale=10))


# plan arrows
flow_arrow(ax2, [(0.55, -0.55), (0.55, -0.02), (0.75, 0.9)], C_IN)
flow_arrow(ax2, [(1.35, -0.55), (1.35, -0.02), (1.25, 0.95)], C_IN)
flow_arrow(ax2, [(0.48, D + 0.6), (0.48, D - 0.05), (0.95, 4.0)], C_IN)
flow_arrow(ax2, [(1.05, 1.5), (0.95, 0.4), (0.95, -0.55)], C_OUT)
flow_arrow(ax2, [(1.9, 1.3), (2.45, 0.3), (2.5, -0.55)], C_OUT)
flow_arrow(ax2, [(1.0, 3.9), (0.55, 4.9), (0.55, D + 0.6)], C_OUT)
flow_arrow(ax2, [(0.8, 2.7), (0.2, 2.05), (-0.9, 2.0)], C_OUT)
flow_arrow(ax2, [(0.4, 3.45), (-0.2, 3.25), (-0.7, 3.2)], C_OUT)
flow_arrow(ax2, [(1.5, 2.9), (1.9, 2.45), (S["x"] - 0.1, S["z"] + 0.05)], C_PL, lw=1.0)
for o in L["occupants"]:
    ax2.add_patch(Circle((o["x"], -o["z"]), 0.13, fc="white", ec=C_PL, lw=1.0, zorder=9))
    ax2.text(o["x"], -o["z"], o["name"], fontsize=6, ha="center", va="center", color=C_PL, fontweight="bold", zorder=10)
labels2 = [
    (0.95, -0.72, "창 하부 틈 · 침기", C_IN), (0.95, -0.47, "창 상부 틈 · 누기", C_OUT), (2.55, -0.72, "에어컨 배관 구멍", C_OUT),
    (0.48, D + 0.72, "현관문 하부 틈 · 침기 / 상부 틈 · 누기", INK), (-0.9, 1.75, "화장실 배기구", C_OUT), (-0.75, 2.95, "주방 후드 덕트", C_OUT),
]
for x, z, s, c in labels2:
    ax2.text(x, -z, s, fontsize=5.8, color=c, ha="center", va="center", zorder=10, bbox=dict(fc="white", ec="none", pad=0.5))
ax2.text(S["x"] - 0.05, -(S["z"] - 0.25), "측정기", fontsize=5.8, color=SIG, ha="center", zorder=10, fontweight="bold")
header(fig2, 14, "틈새바람 · CO₂ 이동 경로 추정도", "개구부를 모두 닫은 상태 · 실내외 온도차(굴뚝효과)에 의한 압력차로 틈새를 통해서만 공기가 오간다고 가정", "평면 1/60 · 단면 1/40")

# side text: legend + numbers
tx0 = 14 + pw2 + 6
ftext(fig2, tx0, 30, "범례", fontsize=7.5, fontweight="bold", color=INK, va="top")
leg = [(C_IN, "침기", "외부·복도 공기가 틈새로 유입"), (C_OUT, "누기", "CO₂가 섞인 실내 공기가 틈새로 유출"),
       (C_PL, "호기 상승·실내 확산", "재실자 A·B·C(위치 가정)의 날숨"), (C_CO, "창 주변 하강 냉기류", "차가운 유리면에서 식은 공기")]
for k, (c, a_, b_) in enumerate(leg):
    y = 37 + k * 9
    lx = fig2.add_axes([tx0 / PAGE_W, 1 - (y + 2) / PAGE_H, 9 / PAGE_W, 3 / PAGE_H]); lx.axis("off"); lx.set_xlim(0, 9); lx.set_ylim(0, 3)
    lx.add_patch(FancyArrowPatch((0.3, 1.5), (8.5, 1.5), arrowstyle="-|>,head_length=0.5,head_width=0.3", color=c, lw=1.4, mutation_scale=10))
    ftext(fig2, tx0 + 11, y - 1, a_, fontsize=6.6, color=INK, va="top", fontweight="bold")
    ftext(fig2, tx0 + 11, y + 2.6, b_, fontsize=5.8, color=MUTED, va="top")
ny = 80
ftext(fig2, tx0, ny, "감소형(Case 2) 구간 분석", fontsize=7.5, fontweight="bold", color=INK, va="top")
ftext(fig2, tx0, ny + 6, r"$C(t) = C_o + (C_0 - C_o)\,e^{-n\,t}$", fontsize=8, color=DIM, va="top")
nums = [
    (f"{n_ach:.2f} 회/h", f"환기횟수 n (R² {r2:.3f})"),
    (f"{n_ach * VOL:.1f} m³/h", "틈새 환기량 Q = n·V"),
    (f"{GEN / 3 * 1000:.0f} L/h", "1인당 CO₂ 발생량 (증가형 물질수지)"),
    (f"약 {n_ach * 20:.1f} 회/h", "ACH50 개략 (n × 20 경험식)"),
]
for k, (v, l) in enumerate(nums):
    y = ny + 13 + k * 10
    ftext(fig2, tx0, y, v, fontsize=9, color=INK, va="top", fontweight="bold")
    ftext(fig2, tx0, y + 4.6, l, fontsize=5.8, color=MUTED, va="top")
ftext(fig2, tx0, ny + 56, f"가정: 외기 CO₂ {CO} ppm\n체적 V = {VOL:.1f} m³\n재실자 위치는 추정", fontsize=5.8, color=MUTED, va="top", linespacing=1.5)

# ---------------- section A-A' (window wall -> entrance), 1/40 ----------------
sec_top = 26 + ph2 + 10
SX0, SX1, SY0, SY1 = -0.75, 5.75, -0.25, 2.55
sw = (SX1 - SX0) * 1000 / 40; sh = (SY1 - SY0) * 1000 / 40
s_left = 10
sx = fig2.add_axes([s_left / PAGE_W, 1 - (sec_top + sh) / PAGE_H, sw / PAGE_W, sh / PAGE_H])
sx.set_xlim(SX0, SX1); sx.set_ylim(SY0, SY1); sx.set_aspect("equal"); sx.axis("off")
ftext(fig2, 14, sec_top - 5, "단면 A–A′ (창문 벽 → 현관, x 약 0.5 m 위치에서 자름)", fontsize=7.5, fontweight="bold", color=INK, va="bottom")
# floor/ceiling slabs and walls
sx.add_patch(Rectangle((-T, -0.16), D + 2 * T, 0.16, fc=POCHE, ec=POCHE))
sx.add_patch(Rectangle((-T, H), D + 2 * T, 0.14, fc=POCHE, ec=POCHE))
sx.add_patch(Rectangle((-T, 0), T, win["y0"], fc=POCHE, ec=POCHE)); sx.add_patch(Rectangle((-T, win["y1"]), T, H - win["y1"], fc=POCHE, ec=POCHE))
sx.add_patch(Rectangle((-T, win["y0"]), T, win["y1"] - win["y0"], fc="white", ec=INK, lw=0.6))
for xx in (-0.03, -0.07):
    sx.plot([xx, xx], [win["y0"], win["y1"]], color=INK, lw=0.5)
sx.add_patch(Rectangle((D, ent["h"]), T, H - ent["h"], fc=POCHE, ec=POCHE))
sx.add_patch(Rectangle((D + 0.03, 0.012), 0.045, ent["h"] - 0.03, fc="#8c9690", ec=INK, lw=0.5))
sx.text(-T / 2, 2.47, "← 외부(창)", fontsize=6.2, ha="center", va="bottom", color=MUTED)
sx.text(D + T / 2, 2.47, "복도(현관) →", fontsize=6.2, ha="center", va="bottom", color=MUTED)
# furniture silhouettes in the section
sx.add_patch(Rectangle((0.02, 0), 0.3, 0.8, fc=FILL, ec="#9aa0a6", lw=0.5))
sx.add_patch(Rectangle((I["mat"]["z0"], 0), I["mat"]["z1"] - I["mat"]["z0"], 0.24, fc=FILL, ec="#9aa0a6", lw=0.5))
sx.add_patch(Rectangle((I["shoeArea"]["z0"], 0), I["shoeArea"]["z1"] - I["shoeArea"]["z0"], 0.01, fc="#cdbda9", ec="none"))
# neutral pressure level
npl = H / 2
sx.plot([0, D], [npl, npl], color=DIM, lw=0.7, ls=(0, (5, 3)))
sx.text(D / 2 + 0.6, npl + 0.05, f"중성대 (NPL, 추정 H/2 약 {npl:.2f} m)", fontsize=6.2, color=DIM, ha="center", va="bottom")
sx.text(2.9, 1.75, "실내압 > 외부  →  위쪽 틈으로 누기", fontsize=6.0, color=C_OUT, ha="center")
sx.text(2.9, 0.42, "실내압 < 외부  →  아래쪽 틈으로 침기", fontsize=6.0, color=C_IN, ha="center")
# occupants (projected) + plumes
for o in L["occupants"]:
    hz, hy = o["z"], o["seat"] + 0.72
    sx.add_patch(Circle((hz, hy), 0.09, fc="#e3d9cc", ec=FUR, lw=0.5, zorder=5))
    sx.add_patch(FancyBboxPatch((hz - 0.1, o["seat"]), 0.2, 0.5, boxstyle="round,pad=0.03", fc="#e3d9cc", ec=FUR, lw=0.5, zorder=5))
    sx.text(hz, o["seat"] + 0.3, o["name"], fontsize=5.6, ha="center", va="center", color=FUR, zorder=6)
    flow_arrow(sx, [(hz, hy + 0.12), (hz, H - 0.05), (hz - 0.6, H - 0.08)], C_PL, lw=1.0, section=True)
# leakage arrows through the cracks
flow_arrow(sx, [(-0.7, 0.93), (-0.05, 0.93), (0.6, 0.55)], C_IN, section=True)
flow_arrow(sx, [(0.8, 1.6), (0.1, 1.97), (-0.7, 1.97)], C_OUT, section=True)
flow_arrow(sx, [(D + 0.5, 0.03), (D - 0.05, 0.03), (D - 0.9, 0.12)], C_IN, section=True)
flow_arrow(sx, [(D - 0.8, 1.65), (D - 0.05, 1.99), (D + 0.5, 1.99)], C_OUT, section=True)
flow_arrow(sx, [(0.12, 1.9), (0.08, 0.9), (0.4, 0.12)], C_CO, lw=1.0, section=True)
# sensor (projected from x = 2.23 m)
sx.add_patch(Circle((S["z"], S["y"]), 0.07, fc=SIG, ec="white", lw=0.5, zorder=8))
sx.add_patch(Rectangle((I["rack"]["z0"], 0), I["rack"]["z1"] - I["rack"]["z0"], 0.955, fc="none", ec="#9aa0a6", lw=0.5, ls=(0, (2, 1.5))))
sx.annotate(f"측정기 H {S['y']:.2f} m (투영)", xy=(S["z"] + 0.05, S["y"]), xytext=(S["z"] + 0.55, 0.95), fontsize=6, color=SIG,
            arrowprops=dict(arrowstyle="-", color=SIG, lw=0.6))
# height dims
for y0_, y1_, lab in ((0, H, mm(H)), (0, npl, mm(npl))):
    xx = -T - 0.5 if lab == mm(H) else -T - 0.3
    sx.plot([xx, xx], [y0_, y1_], color=DIM, lw=0.45)
    for yy in (y0_, y1_):
        sx.plot([xx - 0.05, xx + 0.05], [yy - 0.05, yy + 0.05], color=DIM, lw=0.8)
    sx.text(xx - 0.12, (y0_ + y1_) / 2, lab, fontsize=5.8, color=DIM, rotation=90, va="center")
# stack-effect pressure profile
pp_w = PAGE_W - 10 - (s_left + sw + 4)
pp = fig2.add_axes([(s_left + sw + 4) / PAGE_W, 1 - (sec_top + sh) / PAGE_H, pp_w / PAGE_W, sh / PAGE_H])
pp.set_xlim(-1.3, 1.3); pp.set_ylim(SY0, SY1); pp.axis("off")
pp.plot([0, 0], [0, H], color=INK, lw=0.6)
pp.plot([-1, 1], [0, H], color=DIM, lw=1.1)
pp.fill_betweenx([npl, H], 0, [0, 1], color=C_OUT, alpha=0.15)
pp.fill_betweenx([0, npl], [-1, 0], 0, color=C_IN, alpha=0.15)
pp.plot([-1.1, 1.1], [npl, npl], color=DIM, lw=0.5, ls=(0, (3, 2)))
pp.text(0.55, H * 0.92, "+ΔP", fontsize=6, color=C_OUT, ha="center")
pp.text(-0.55, H * 0.06, "-ΔP", fontsize=6, color=C_IN, ha="center")
pp.text(0, -0.08, "실내-실외\n압력차", fontsize=5.6, color=MUTED, ha="center", va="top", linespacing=1.3)
ftext(fig2, 14, sec_top + sh + 8, "· 11월 저녁 측정: 실내 18.5–19.6 °C > 외기 → 따뜻한 실내 공기가 위로 올라가 상부 틈으로 빠지고(누기), 하부 틈으로 외기가 들어온다(침기).", fontsize=6, color=INK, va="top")
ftext(fig2, 14, sec_top + sh + 13, "· Case 1에서는 재실자 날숨(CO₂)이 상승기류를 타고 천장 쪽에 퍼진 뒤 섞이며, 누기 경로로 CO₂가 함께 빠져나간다.", fontsize=6, color=INK, va="top")
ftext(fig2, 14, sec_top + sh + 18, "· Case 2에서는 발생원이 없으므로 침기·누기에 의한 희석만으로 농도가 지수적으로 감소하며, 그 감소 속도가 기밀성(n)을 나타낸다.", fontsize=6, color=INK, va="top")
ftext(fig2, 14, sec_top + sh + 23, "· 화장실 배기구와 주방 후드 덕트는 수직 덕트의 굴뚝효과로 약한 흡인(부압)이 생긴다고 가정했다. 모든 경로는 측정값이 아닌 추정이다.", fontsize=6, color=INK, va="top")
title_block(fig2, 14, PAGE_W - 28, 264, [
    ("과목", "환경설비실험", "실험", "실내 CO₂ 농도 측정 (10주차)", "축척", "평면 1/60 · 단면 1/40", "단위", "mm, m"),
    ("도면", "틈새바람 추정도", "비고", "경로는 압력차 원리에 따른 추정, 측정값 아님", "작성일", "2026.11.11", "도면번호", "A-02"),
])

with PdfPages(OUT / "자취방_평면도.pdf") as pdf:
    pdf.savefig(fig1); pdf.savefig(fig2)
fig1.savefig(OUT / "자취방_평면도.png", dpi=220)
fig2.savefig(OUT / "자취방_공기흐름도.png", dpi=220)
print(f"saved; area {AREA:.2f} m2, volume {VOL:.2f} m3, n {n_ach:.3f}/h, R2 {r2:.4f}, Q {n_ach * VOL:.2f}, G/person {GEN / 3 * 1000:.1f} L/h")
