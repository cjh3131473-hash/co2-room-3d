"""layout.json + Co2 측정.csv -> ../자취방_3D.html

실측 치수로 바꾸려면 layout.json 을 고친 뒤:  python build.py && python plan.py
"""
import csv
import json
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
for name in ("자취방_3D.html", "index.html"):   # index.html = GitHub Pages 첫 화면
    (OUT_DIR / name).write_text(html, encoding="utf-8")
print("wrote 자취방_3D.html + index.html", len(html), "bytes;", len(rows), "rows")
