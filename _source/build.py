"""layout.json + Co2 측정.csv -> ../index.html (= ../자취방_3D.html), ../presentation/index.html

- index.html, 자취방_3D.html : 기존 프로그램 (발표 모드 코드 없음)
- presentation/index.html    : 같은 3D에 발표 모드를 켠 페이지 (환경설비실험 CO₂ 측정 발표 1조)

실측 치수로 바꾸려면 layout.json 을 고친 뒤:  python build.py && python plan.py
"""
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent
CSV = OUT_DIR.parent / "Co2 측정.csv"

layout = json.loads((HERE / "layout.json").read_text(encoding="utf-8"))

rows = list(csv.reader(CSV.open(encoding="cp949")))[3:]
rows = [r for r in rows if len(r) >= 5 and r[2].strip()]
data = {
    "start": rows[0][0],
    "step": 60,
    "co2": [int(float(r[2])) for r in rows],
    "temp": [float(r[3]) for r in rows],
    "rh": [float(r[4]) for r in rows],
}

html = (HERE / "template.html").read_text(encoding="utf-8")
html = html.replace("/*__LAYOUT__*/null", json.dumps(layout, ensure_ascii=False))
html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))

# 기존 프로그램: 발표 모드 화면 요소를 빼고 PRESENT = false 그대로
normal = re.sub(r"<!--PRESENT-->.*?<!--/PRESENT-->\n?", "", html, flags=re.S)
for name in ("자취방_3D.html", "index.html"):   # index.html = GitHub Pages 첫 화면
    (OUT_DIR / name).write_text(normal, encoding="utf-8")

# 발표 페이지
deck = html.replace("/*__PRESENT__*/false", "true")
deck = deck.replace("<title>CO₂ 측정 자취방 3D</title>", "<title>환경설비실험 CO₂ 측정 발표 1조</title>")
deck = deck.replace("<!--PRESENT-->\n", "").replace("<!--/PRESENT-->\n", "")
(OUT_DIR / "presentation").mkdir(exist_ok=True)
(OUT_DIR / "presentation" / "index.html").write_text(deck, encoding="utf-8")
print("wrote index.html + 자취방_3D.html", len(normal), "/ presentation/index.html", len(deck), ";", len(rows), "rows")
