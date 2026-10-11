"""Generate a static HTML dashboard from failures.db.

Run:  python dashboard.py                # uses failures.db
      python dashboard.py demo.db        # uses another database
Then open dashboard.html in your browser (screenshot it for LinkedIn/GitHub).
No extra dependencies: charts are inline SVG, so the file works offline.
"""
import html
import sys
from collections import Counter
from pathlib import Path

from fpm.storage import FailureStore

SEV_COLORS = {"low": "#22c55e", "medium": "#eab308", "high": "#f97316", "critical": "#ef4444"}
BAR_COLOR = "#2563eb"


def load_failures(db_path: str) -> list:
    store = FailureStore(db_path)
    try:
        return store.get_all()
    finally:
        store.close()


def bar_chart(counts: Counter, title: str, color_for=None) -> str:
    if not counts:
        return f"<div class='panel'><h3>{html.escape(title)}</h3><p class='muted'>No data yet.</p></div>"

    width, row_h, label_w = 460, 32, 175
    bar_max = width - label_w - 45
    items = counts.most_common()
    max_v = max(v for _, v in items)
    height = len(items) * row_h + 6

    parts = []
    for i, (label, v) in enumerate(items):
        y = i * row_h + 4
        w = max(4, int(bar_max * v / max_v))
        color = color_for(label) if color_for else BAR_COLOR
        parts.append(
            f'<text x="0" y="{y + 19}" class="lbl">{html.escape(str(label))}</text>'
            f'<rect x="{label_w}" y="{y + 5}" width="{w}" height="18" rx="4" fill="{color}"/>'
            f'<text x="{label_w + w + 8}" y="{y + 19}" class="val">{v}</text>'
        )
    return (
        f"<div class='panel'><h3>{html.escape(title)}</h3>"
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="{html.escape(title)}">'
        + "".join(parts) + "</svg></div>"
    )


def build_html(rows: list) -> str:
    total = len(rows)
    sev = Counter(r["severity"] for r in rows)
    cat = Counter(r["error_category"] for r in rows)
    task = Counter(r["task_type"] for r in rows)
    high = sev.get("high", 0) + sev.get("critical", 0)

    cards = [
        ("Failures recorded", total),
        ("High or critical", high),
        ("Error categories", len(cat)),
        ("Task types", len(task)),
    ]
    card_html = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="lab">{k}</div></div>'
        for k, v in cards
    )

    sev_order = ["low", "medium", "high", "critical"]
    sev_sorted = Counter({k: sev[k] for k in sev_order if k in sev} | {k: v for k, v in sev.items() if k not in sev_order})

    table_rows = "".join(
        "<tr>"
        f"<td>{html.escape(r['timestamp'][:16].replace('T', ' '))}</td>"
        f"<td>{html.escape(r['error_category'])}</td>"
        f"<td>{html.escape(r['context_pattern'])}</td>"
        f"<td>{html.escape(r['task_type'])}</td>"
        f"<td><span class='pill' style='background:{SEV_COLORS.get(r['severity'], '#64748b')}'>"
        f"{html.escape(r['severity'])}</span></td>"
        "</tr>"
        for r in rows[:50]
    ) or "<tr><td colspan='5' class='muted'>No failures recorded yet.</td></tr>"

    charts = (
        bar_chart(sev_sorted, "Failures by severity",
                  color_for=lambda s: SEV_COLORS.get(s, "#64748b"))
        + bar_chart(cat, "Failures by error category")
        + bar_chart(task, "Failures by task type")
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Failure Pattern Memory - Dashboard</title>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:#f8fafc;
         color:#0f172a; margin:0; padding:32px; }}
  header h1 {{ margin:0 0 4px; font-size:28px; }}
  header p {{ margin:0 0 24px; color:#64748b; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin-bottom:24px; }}
  .card {{ background:#fff; border-radius:12px; padding:18px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .num {{ font-size:32px; font-weight:700; color:#2563eb; }}
  .lab {{ color:#64748b; font-size:14px; }}
  .charts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; margin-bottom:24px; }}
  .panel {{ background:#fff; border-radius:12px; padding:18px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .panel h3 {{ margin:0 0 12px; font-size:16px; }}
  svg .lbl {{ font-size:13px; fill:#334155; }}
  svg .val {{ font-size:13px; fill:#0f172a; font-weight:600; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden;
          box-shadow:0 1px 3px rgba(0,0,0,.08); font-size:14px; }}
  th, td {{ text-align:left; padding:10px 14px; border-bottom:1px solid #e2e8f0; }}
  th {{ background:#0f172a; color:#fff; font-weight:600; }}
  .pill {{ color:#fff; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600; }}
  .muted {{ color:#64748b; }}
  footer {{ margin-top:16px; color:#94a3b8; font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Failure Pattern Memory</h1>
  <p>Recorded agent failures and the patterns behind them</p>
</header>
<section class="cards">{card_html}</section>
<section class="charts">{charts}</section>
<h2 style="font-size:18px">Recent failures</h2>
<table>
  <thead><tr><th>Time (UTC)</th><th>Category</th><th>Pattern</th><th>Task</th><th>Severity</th></tr></thead>
  <tbody>{table_rows}</tbody>
</table>
<footer>Generated from the failure database. Total records: {total}.</footer>
</body>
</html>
"""


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else "failures.db"
    if not Path(db).exists():
        sys.exit(f"Database not found: {db}. Run demo.py or 'fpm record' first.")
    rows = load_failures(db)
    out = Path("dashboard.html")
    out.write_text(build_html(rows), encoding="utf-8")
    print(f"Wrote {out.resolve()} ({len(rows)} failures)")


if __name__ == "__main__":
    main()
