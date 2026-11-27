"""Builds dashboard.html: a self-contained, styled page with no external dependencies.

Layout: sidebar navigation, a summary of the snapshot, a "today's attention" list,
suggested actions for a person to decide on, and the detail sections.
Nothing on the page changes records; every action needs a person to approve it.

Usage:  python3 build_dashboard.py   (then open dashboard.html in a browser)
"""

import html
import math
from pathlib import Path

import analysis as a

OUT = Path(__file__).parent / "dashboard.html"

TIER_CLASS = {"High": "high", "Medium": "medium", "Low": "low"}
RING_RADIUS = 38
RING_CIRCUMFERENCE = 2 * math.pi * RING_RADIUS
TIER_COLOR = {"high": "#b42318", "medium": "#b54708", "low": "#067647"}


def esc(x):
    return html.escape(str(x))


def pct(x, digits=1):
    return f"{x:.{digits}%}"


def status_color(achievement):
    if achievement >= 0.9:
        return "#067647"
    if achievement >= 0.8:
        return "#b54708"
    return "#b42318"


def ring(value, color):
    filled = max(0.0, min(1.0, value)) * RING_CIRCUMFERENCE
    return f"""<svg class="ring" viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="{RING_RADIUS}" class="ring-bg"/>
      <circle cx="50" cy="50" r="{RING_RADIUS}" class="ring-fg" stroke="{color}"
        stroke-dasharray="{filled:.2f} {RING_CIRCUMFERENCE:.2f}"/>
    </svg>"""


def meter(value, color):
    width = max(0.0, min(1.0, value)) * 100
    return f'<div class="meter"><div class="meter-fill" style="width:{width:.1f}%;background:{color}"></div></div>'


def build():
    r = a.run_all()
    lines, machines, batches = r["lines"], r["machines"], r["batches"]

    lines_data, _, _ = a.load_inputs()
    target = sum(l["daily_target"] for l in lines_data)
    actual = sum(l["actual_output"] for l in lines_data)
    defects = sum(l["defective_units"] for l in lines_data)
    downtime_pct = sum(l["downtime_hours_per_day"] for l in lines_data) / (16 * len(lines_data))
    material_var = sum(b["variance_kg"] for b in batches)
    material_var_pct = material_var / sum(b["expected_kg"] for b in batches)
    high = [m for m in machines if m["tier"] == "High"]
    worst_line = min(lines, key=lambda l: l["achievement"])
    worst_batch = max(batches, key=lambda b: b["variance_pct"])
    top_machine = machines[0]

    # ---- Summary cards -------------------------------------------------
    kpis = [
        ("Overall achievement", pct(actual / target), f"{actual:,.0f} of {target:,.0f} units", status_color(actual / target)),
        ("Units short", f"{target - actual:,.0f}", f"{worst_line['line']} accounts for {worst_line['shortfall_units']:,.0f}", "#b42318"),
        ("Defect rate", pct(defects / actual), f"{defects:,.0f} defective units", "#b54708"),
        ("Downtime", pct(downtime_pct), "of scheduled hours, all lines", "#b54708"),
        ("High-risk machines", str(len(high)), f"out of {len(machines)} observed", "#b42318" if high else "#067647"),
        ("Material over expected", f"{material_var:+,.0f} kg", f"{material_var_pct:+.1%} across four batches", "#b54708"),
    ]
    kpi_html = "".join(
        f"""<div class="kpi"><div class="kpi-top"><span class="dot" style="background:{accent}"></span>
          <span class="kpi-label">{esc(label)}</span></div>
          <div class="kpi-value">{esc(value)}</div>
          <div class="kpi-note">{esc(note)}</div></div>"""
        for label, value, note, accent in kpis
    )

    # ---- Today's attention ---------------------------------------------
    attention = [
        ("high", f"{worst_line['line']} is the largest gap",
         f"{pct(worst_line['achievement'])} achievement, {worst_line['shortfall_units']:,.0f} units short, {pct(worst_line['downtime_pct'])} downtime.",
         "Review the downtime causes on this line first."),
        ("high", f"{top_machine['machine']} is High risk",
         f"Score {top_machine['risk_score']:.2f}: {top_machine['temperature_c']:.0f} °C, {top_machine['vibration_mm_s']:.1f} mm/s, {top_machine['defects']:.0f} defects.",
         "Inspect against the manufacturer's alarm limits before any other action."),
        ("medium", f"{worst_batch['batch']} used more material",
         f"{worst_batch['variance_kg']:+.0f} kg ({worst_batch['variance_pct']:+.1%}) over expected.",
         "Check the batch record and weighing for this run."),
    ]
    attention_html = "".join(
        f"""<div class="item {sev}">
          <div class="item-main"><div class="item-title">{esc(title)}</div>
          <div class="item-body">{esc(body)}</div></div>
          <div class="item-side"><span class="status">Awaiting review</span>
          <div class="item-action">Suggested: {esc(action)}</div></div></div>"""
        for sev, title, body, action in attention
    )

    # ---- Suggested actions (for a person to decide) ---------------------
    actions = [
        f"Inspect {top_machine['machine']}, {', '.join(m['machine'] for m in high[1:])} against manufacturer alarm limits, which the case study does not provide.",
        f"Find out why {worst_line['line']} lost {worst_line['downtime_pct']*16:.1f} hours a day. Only about {worst_line['downtime_loss_units']:,.0f} of its {worst_line['shortfall_units']:,.0f} missing units are explained by downtime.",
        "Add a line ID and timestamps to every machine reading, so machine totals can be matched to line totals.",
        f"Check the material records for {worst_batch['batch']} and {batches[3]['batch']}, which are over expected, and confirm which line {batches[3]['batch']} came from.",
    ]
    action_html = "".join(f"<li>{esc(x)}</li>" for x in actions)

    # ---- Detail sections ----------------------------------------------
    line_cards = "".join(
        f"""<div class="card">
          <div class="card-head"><div class="line-name">{esc(l['line'])}</div>
            <div class="line-achv" style="color:{status_color(l['achievement'])}">{pct(l['achievement'])}</div></div>
          <div class="ring-wrap">{ring(l['oee_estimate'], status_color(l['achievement']))}
            <div class="ring-center"><div class="ring-num">{pct(l['oee_estimate'], 0)}</div>
            <div class="ring-sub">OEE est.</div></div></div>
          <div class="stat-row"><span>Defect rate</span><strong>{pct(l['defect_rate'])}</strong></div>
          <div class="stat-row"><span>Downtime</span><strong>{pct(l['downtime_pct'])}</strong></div>
          <div class="stat-row"><span>Shortfall</span><strong>{l['shortfall_units']:,.0f} units</strong></div>
          <div class="stat-row muted"><span>Not explained by downtime</span><strong>{l['unexplained_shortfall_units']:,.0f} units</strong></div>
        </div>"""
        for l in lines
    )

    machine_rows = "".join(
        f"""<div class="machine-row">
          <div class="machine-id">{esc(m['machine'])}</div>
          {meter(m['risk_score'], TIER_COLOR[TIER_CLASS[m['tier']]])}
          <div class="machine-score">{m['risk_score']:.2f}</div>
          <span class="pill {TIER_CLASS[m['tier']]}">{m['tier']}</span>
          <div class="machine-stats">{m['temperature_c']:.0f} °C · {m['vibration_mm_s']:.1f} mm/s · {m['downtime_hours']:.1f} h · {m['defects']:.0f} defects</div>
        </div>"""
        for m in machines
    )

    max_batch = max(abs(b["variance_pct"]) for b in batches) or 1
    batch_rows = "".join(
        f"""<div class="batch-row">
          <div class="batch-id">{esc(b['batch'])}</div>
          <div class="batch-val">{b['variance_kg']:+.0f} kg <span class="muted">({b['variance_pct']:+.1%})</span></div>
          <div class="batch-bar"><div class="batch-fill {'over' if b['variance_kg'] > 0 else 'under'}"
            style="width:{abs(b['variance_pct']) / max_batch * 100:.1f}%"></div></div>
          <div class="batch-meta">{b['used_kg']:.0f} used · {b['expected_kg']:.0f} expected · {b['output']:.0f} units · {b['rejected']:.0f} rejected</div>
        </div>"""
        for b in batches
    )

    warning_items = "".join(f"<li>{esc(x)}</li>" for x in r["warnings"])

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Track B: Manufacturing Intelligence Dashboard</title>
<style>
  :root {{ --bg:#f5f6f3; --card:#ffffff; --ink:#1c2430; --muted:#637083; --line:#e3e7ec;
           --accent:#0f766e; --accent-soft:#e6f4f2; --high:#b42318; --med:#b54708; --low:#067647; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          background: var(--bg); color: var(--ink); line-height: 1.45; }}
  .layout {{ display:grid; grid-template-columns: 220px 1fr; min-height:100vh; }}
  nav {{ background:#fff; border-right:1px solid var(--line); padding:1.4rem 1rem; position:sticky; top:0; height:100vh; }}
  .brand {{ font-weight:800; letter-spacing:-.01em; font-size:1.05rem; }}
  .brand small {{ display:block; color:var(--muted); font-weight:500; font-size:.78rem; margin-top:.15rem; }}
  nav .group {{ color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.1em; margin:1.4rem 0 .4rem .5rem; }}
  nav a {{ display:block; color:var(--ink); text-decoration:none; padding:.5rem .65rem; border-radius:8px; font-size:.92rem; }}
  nav a:hover {{ background:var(--accent-soft); }}
  nav a.active {{ background:var(--accent-soft); color:var(--accent); font-weight:650; }}
  .demo {{ margin-top:1.6rem; background:#fff7e6; border:1px solid #f2d59b; color:#7a4e00; border-radius:10px; padding:.6rem .7rem; font-size:.78rem; }}
  main {{ padding: 1.6rem 2rem 2.5rem; }}
  header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; flex-wrap:wrap; margin-bottom:1.1rem; }}
  h1 {{ margin:0; font-size:1.7rem; letter-spacing:-.02em; }}
  .sub {{ color:var(--muted); margin:.25rem 0 0; }}
  .pillbar {{ display:flex; gap:.5rem; flex-wrap:wrap; }}
  .chip {{ background:#fff; border:1px solid var(--line); border-radius:999px; padding:.35rem .75rem; font-size:.8rem; color:var(--muted); }}
  .chip.strong {{ color:var(--accent); border-color:#9fd6cf; }}
  .notice {{ background:#fff; border:1px solid var(--line); border-left:4px solid var(--med); border-radius:10px; padding:.7rem 1rem; font-size:.9rem; margin-bottom:1.2rem; }}
  section {{ margin-bottom:1.4rem; scroll-margin-top: 1rem; }}
  h2 {{ font-size:1.05rem; margin:0 0 .15rem; }}
  .hint {{ color:var(--muted); font-size:.85rem; margin:0 0 .8rem; }}
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1.1rem 1.2rem; }}

  .kpis {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px,1fr)); gap:.8rem; }}
  .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:.9rem 1rem; }}
  .kpi-top {{ display:flex; align-items:center; gap:.45rem; }}
  .dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}
  .kpi-label {{ color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.05em; font-weight:650; }}
  .kpi-value {{ font-size:1.6rem; font-weight:750; margin:.3rem 0 .05rem; letter-spacing:-.02em; }}
  .kpi-note {{ color:var(--muted); font-size:.8rem; }}

  .grid-2 {{ display:grid; grid-template-columns: 1fr 1fr; gap:1.1rem; }}
  @media (max-width: 960px) {{ .grid-2 {{ grid-template-columns:1fr; }} .layout {{ grid-template-columns:1fr; }} nav {{ position:static; height:auto; }} }}

  .item {{ display:flex; justify-content:space-between; gap:1rem; padding:.85rem 0; border-top:1px solid var(--line); }}
  .item:first-of-type {{ border-top:0; padding-top:0; }}
  .item-title {{ font-weight:650; }}
  .item-body {{ color:var(--muted); font-size:.88rem; }}
  .item-side {{ text-align:right; min-width:200px; }}
  .item-action {{ font-size:.82rem; color:var(--ink); margin-top:.3rem; }}
  .status {{ display:inline-block; font-size:.72rem; font-weight:650; background:#f1f3f5; color:var(--muted); padding:.15rem .55rem; border-radius:999px; }}
  .item.high .item-title::before {{ content:""; display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--high); margin-right:.5rem; }}
  .item.medium .item-title::before {{ content:""; display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--med); margin-right:.5rem; }}

  .actions {{ margin:0; padding-left:1.2rem; }}
  .actions li {{ margin:.5rem 0; }}

  .lines {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px,1fr)); gap:.9rem; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem; }}
  .card-head {{ display:flex; justify-content:space-between; align-items:center; }}
  .line-name {{ font-weight:700; }}
  .line-achv {{ font-weight:800; font-size:1.05rem; }}
  .ring-wrap {{ position:relative; width:124px; height:124px; margin:.5rem auto .7rem; }}
  .ring {{ width:100%; height:100%; transform:rotate(-90deg); }}
  .ring-bg {{ fill:none; stroke:#e9edf1; stroke-width:10; }}
  .ring-fg {{ fill:none; stroke-width:10; stroke-linecap:round; }}
  .ring-center {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
  .ring-num {{ font-size:1.4rem; font-weight:800; }}
  .ring-sub {{ color:var(--muted); font-size:.7rem; }}
  .stat-row {{ display:flex; justify-content:space-between; font-size:.86rem; padding:.3rem 0; border-top:1px dashed var(--line); }}
  .stat-row span {{ color:var(--muted); }}
  .stat-row.muted strong {{ color:var(--muted); font-weight:600; }}

  .machine-row {{ display:grid; grid-template-columns: 56px 1fr 44px 74px; gap:.6rem; align-items:center; padding:.6rem 0; border-top:1px solid var(--line); }}
  .machine-row:first-of-type {{ border-top:0; }}
  .machine-id {{ font-weight:700; }}
  .machine-score {{ text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; font-size:.85rem; }}
  .machine-stats {{ grid-column: 2 / 5; color:var(--muted); font-size:.8rem; margin-top:-.25rem; }}
  .meter {{ height:8px; background:#e9edf1; border-radius:999px; overflow:hidden; }}
  .meter-fill {{ height:100%; border-radius:999px; }}
  .pill {{ justify-self:start; padding:.15rem .6rem; border-radius:999px; font-size:.72rem; font-weight:700; }}
  .pill.high {{ background:#fde8e6; color:var(--high); }}
  .pill.medium {{ background:#fdf0dc; color:var(--med); }}
  .pill.low {{ background:#dcf5e7; color:var(--low); }}

  .batch-row {{ padding:.6rem 0; border-top:1px solid var(--line); }}
  .batch-row:first-of-type {{ border-top:0; }}
  .batch-id {{ display:inline-block; font-weight:700; width:56px; }}
  .batch-val {{ display:inline-block; font-weight:700; font-variant-numeric:tabular-nums; }}
  .batch-bar {{ height:8px; background:#e9edf1; border-radius:999px; margin:.4rem 0 .3rem; overflow:hidden; }}
  .batch-fill {{ height:100%; border-radius:999px; }}
  .batch-fill.over {{ background:var(--med); }}
  .batch-fill.under {{ background:var(--low); }}
  .batch-meta {{ color:var(--muted); font-size:.8rem; }}
  .muted {{ color:var(--muted); }}

  .warnings ul {{ margin:0; padding-left:1.1rem; }}
  .warnings li {{ margin:.45rem 0; font-size:.9rem; }}

  .flow {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:.7rem; }}
  .step {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:.8rem .9rem; }}
  .step b {{ color:var(--accent); font-size:.8rem; letter-spacing:.06em; text-transform:uppercase; }}
  .step p {{ margin:.3rem 0 0; font-size:.86rem; color:var(--muted); }}
  @media (max-width: 760px) {{ .flow {{ grid-template-columns:1fr 1fr; }} .item {{ flex-direction:column; }} .item-side {{ text-align:left; min-width:0; }} }}
  footer {{ color:var(--muted); font-size:.8rem; margin-top:1.5rem; }}
</style></head>
<body>
<div class="layout">
  <nav>
    <div class="brand">Manufacturing Intelligence<small>PrecisionWorks · Track B prototype</small></div>
    <div class="group">Overview</div>
    <a href="#snapshot" class="active">Snapshot</a>
    <a href="#attention">Today's attention</a>
    <a href="#actions">Suggested actions</a>
    <div class="group">Detail</div>
    <a href="#lines">Production lines</a>
    <a href="#machines">Machine risk</a>
    <a href="#materials">Material by batch</a>
    <a href="#checks">Data checks</a>
    <div class="group">About</div>
    <a href="#how">How it works</a>
    <div class="demo">Illustrative data from the case study. Nothing on this page changes records. A person approves every action.</div>
  </nav>

  <main>
    <header>
      <div>
        <h1>Factory performance snapshot</h1>
        <p class="sub">Three production lines · six machines · one day of case study data</p>
      </div>
      <div class="pillbar">
        <span class="chip strong">Single-day snapshot</span>
        <span class="chip">Human approval required</span>
      </div>
    </header>

    <div class="notice"><strong>Not measured results.</strong> These figures come from the case study tables. The 30- and 90-day impact figures are a plan, not outcomes.</div>

    <section id="snapshot">
      <div class="kpis">{kpi_html}</div>
    </section>

    <section id="attention">
      <div class="panel">
        <h2>Today's attention</h2>
        <p class="hint">What needs a look first, ranked by impact. Each item waits for a person to review it.</p>
        {attention_html}
      </div>
    </section>

    <section id="actions">
      <div class="panel">
        <h2>Suggested actions</h2>
        <p class="hint">Suggestions for a manager or engineer to decide on. They are generated from the rules in analysis.py and are not instructions.</p>
        <ol class="actions">{action_html}</ol>
      </div>
    </section>

    <section id="lines">
      <div class="panel">
        <h2>Production lines</h2>
        <p class="hint">Green at 90% achievement or above, amber at 80–90%, red below 80%. OEE is an estimate: achievement × quality.</p>
        <div class="lines">{line_cards}</div>
      </div>
    </section>

    <div class="grid-2">
      <section id="machines">
        <div class="panel">
          <h2>Machine risk</h2>
          <p class="hint">Weighted rule: vibration 35%, temperature 25%, downtime 20%, defects 20%, scaled to the highest value in the sample. High ≥ 0.75, Medium ≥ 0.50. Check against manufacturer alarm limits.</p>
          {machine_rows}
        </div>
      </section>
      <section id="materials">
        <div class="panel">
          <h2>Material by batch</h2>
          <p class="hint">Material used against expected. Amber means over expected; green means under. Bar length is relative to the largest variance.</p>
          {batch_rows}
        </div>
      </section>
    </div>

    <section id="checks">
      <div class="panel warnings">
        <h2>Data checks</h2>
        <p class="hint">Inconsistencies in the input data. Resolve these before trusting any single number.</p>
        <ul>{warning_items}</ul>
      </div>
    </section>

    <section id="how">
      <h2>How it works</h2>
      <p class="hint">The same loop every week, so anyone on the team can follow it and check it.</p>
      <div class="flow">
        <div class="step"><b>1 · Detect</b><p>Rules and KPIs flag lines, machines and batches that need a look.</p></div>
        <div class="step"><b>2 · Explain</b><p>Every number shows its inputs and formula, so it can be challenged.</p></div>
        <div class="step"><b>3 · Approve</b><p>A person reviews each item and decides what to do. Nothing is automatic.</p></div>
        <div class="step"><b>4 · Learn</b><p>Recorded outcomes become the labels a future model would need.</p></div>
      </div>
    </section>

    <footer>Generated by build_dashboard.py from analysis.py · edit the CSV files in data/ and re-run to refresh.</footer>
  </main>
</div>
</body></html>
"""
    OUT.write_text(page, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    print("Wrote", build())
