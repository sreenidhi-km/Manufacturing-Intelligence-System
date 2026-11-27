"""Builds dashboard.html: a self-contained, styled page with no external dependencies.

Layout: a top bar, a headline with the factory output bar (target vs made vs lost),
a key-figure strip, what needs attention, suggested next steps, then the detail:
production lines, machine risk, material by batch, data checks and how it works.
Nothing on the page changes records; every action needs a person to approve it.

Usage:  python3 build_dashboard.py   (then open dashboard.html in a browser)
"""

import html
from pathlib import Path

import analysis as a

OUT = Path(__file__).parent / "dashboard.html"

TIER_CLASS = {"High": "high", "Medium": "medium", "Low": "low"}


def esc(x):
    return html.escape(str(x))


def pct(x, digits=1):
    return f"{x:.{digits}%}"


def status_class(achievement):
    if achievement >= 0.9:
        return "ok"
    if achievement >= 0.8:
        return "warn"
    return "bad"


def build():
    r = a.run_all()
    lines, machines, batches = r["lines"], r["machines"], r["batches"]

    lines_data, _, _ = a.load_inputs()
    targets = {l["production_line"]: l["daily_target"] for l in lines_data}
    actuals = {l["production_line"]: l["actual_output"] for l in lines_data}
    target = sum(targets.values())
    actual = sum(actuals.values())
    defects = sum(l["defective_units"] for l in lines_data)
    downtime_pct = sum(l["downtime_hours_per_day"] for l in lines_data) / (16 * len(lines_data))
    material_var = sum(b["variance_kg"] for b in batches)
    material_var_pct = material_var / sum(b["expected_kg"] for b in batches)
    high = [m for m in machines if m["tier"] == "High"]
    worst_line = min(lines, key=lambda l: l["achievement"])
    worst_batch = max(batches, key=lambda b: b["variance_pct"])
    top_machine = machines[0]
    lost_downtime = sum(l["downtime_loss_units"] for l in lines)
    lost_other = sum(l["unexplained_shortfall_units"] for l in lines)

    # ---- Hero: factory output bar --------------------------------------
    shades = ["#1f5bd8", "#3f78e6", "#6c98ef"]
    made_segments = "".join(
        f"""<div class="seg made" style="flex:{actuals[l['line']]};background:{shades[i % 3]}"
             title="{esc(l['line'])}: {actuals[l['line']]:,.0f} units made">
             <span>{esc(l['line'])}<b>{actuals[l['line']]:,.0f}</b></span></div>"""
        for i, l in enumerate(lines)
    )
    hero_bar = f"""<div class="output-bar" role="img"
        aria-label="{actual:,.0f} of {target:,.0f} units made. {lost_downtime:,.0f} lost to downtime, {lost_other:,.0f} lost to unrecorded causes.">
        {made_segments}
        <div class="seg lost-down" style="flex:{lost_downtime:.2f}" title="Lost to downtime: about {lost_downtime:,.0f} units"></div>
        <div class="seg lost-other" style="flex:{lost_other:.2f}" title="Lost to unrecorded causes: about {lost_other:,.0f} units"></div>
      </div>
      <div class="bar-scale"><span>0</span><span>Daily target {target:,.0f}</span></div>
      <ul class="legend">
        <li><i class="sw made"></i>Made: {actual:,.0f} units</li>
        <li><i class="sw lost-down"></i>Lost to downtime: about {lost_downtime:,.0f}</li>
        <li><i class="sw lost-other"></i>Lost, cause not recorded: about {lost_other:,.0f}</li>
      </ul>"""

    # ---- Key figures strip --------------------------------------------
    figures = [
        ("Achievement", pct(actual / target), f"{actual:,.0f} of {target:,.0f} units", status_class(actual / target)),
        ("Defect rate", pct(defects / actual), f"{defects:,.0f} defective units", "warn"),
        ("Downtime", pct(downtime_pct), "of scheduled hours", "warn"),
        ("High-risk machines", f"{len(high)} of {len(machines)}", ", ".join(m["machine"] for m in high) or "None", "bad" if high else "ok"),
        ("Material over expected", f"{material_var:+,.0f} kg", f"{material_var_pct:+.1%} across {len(batches)} batches", "warn"),
    ]
    figures_html = "".join(
        f"""<div class="fig {cls}"><div class="fig-label">{esc(label)}</div>
          <div class="fig-value">{esc(value)}</div><div class="fig-note">{esc(note)}</div></div>"""
        for label, value, note, cls in figures
    )

    # ---- Needs attention ---------------------------------------------
    attention = [
        ("high", "High", f"{worst_line['line']} has the largest gap",
         f"{pct(worst_line['achievement'])} of target, {worst_line['shortfall_units']:,.0f} units short, {pct(worst_line['downtime_pct'])} downtime.",
         "Review the downtime causes on this line first."),
        ("high", "High", f"{top_machine['machine']} has the highest risk score",
         f"Score {top_machine['risk_score']:.2f}: {top_machine['temperature_c']:.0f} °C, {top_machine['vibration_mm_s']:.1f} mm/s, {top_machine['defects']:.0f} defects.",
         "Inspect against the manufacturer's alarm limits before any other action."),
        ("medium", "Medium", f"{worst_batch['batch']} used the most extra material",
         f"{worst_batch['variance_kg']:+.0f} kg ({worst_batch['variance_pct']:+.1%}) over expected.",
         "Check the batch record and weighing for this run."),
    ]
    attention_html = "".join(
        f"""<article class="alert {sev}">
          <div class="alert-head"><span class="sev">{sev_label}</span><span class="state">Awaiting review</span></div>
          <h3>{esc(title)}</h3><p>{esc(body)}</p>
          <p class="suggest"><span>Suggested</span>{esc(action)}</p></article>"""
        for sev, sev_label, title, body, action in attention
    )

    # ---- Suggested next steps ------------------------------------------
    actions = [
        f"Inspect {', '.join(m['machine'] for m in high)} against manufacturer alarm limits, which the case study does not provide.",
        f"Find out why {worst_line['line']} lost {worst_line['downtime_pct']*16:.1f} hours a day. Only about {worst_line['downtime_loss_units']:,.0f} of its {worst_line['shortfall_units']:,.0f} missing units are explained by downtime.",
        "Add a line ID and timestamps to every machine reading, so machine totals can be matched to line totals.",
        f"Check the material records for {worst_batch['batch']} and {batches[3]['batch']}, which are over expected, and confirm which line {batches[3]['batch']} came from.",
    ]
    action_html = "".join(f"<li>{esc(x)}</li>" for x in actions)

    # ---- Production lines: one lane per line ----------------------------
    lane_html = ""
    for l in lines:
        t = targets[l["line"]]
        made = actuals[l["line"]] / t * 100
        down = l["downtime_loss_units"] / t * 100
        other = l["unexplained_shortfall_units"] / t * 100
        cls = status_class(l["achievement"])
        lane_html += f"""<div class="lane">
          <div class="lane-name"><span class="led {cls}"></span>{esc(l['line'])}
            <small>target {t:,.0f}</small></div>
          <div class="lane-track" title="{actuals[l['line']]:,.0f} made of {t:,.0f}">
            <div class="lt made" style="width:{made:.2f}%"><span>{pct(l['achievement'])}</span></div>
            <div class="lt lost-down" style="width:{down:.2f}%"></div>
            <div class="lt lost-other" style="width:{other:.2f}%"></div>
          </div>
          <dl class="lane-stats">
            <div><dt>OEE est.</dt><dd>{pct(l['oee_estimate'])}</dd></div>
            <div><dt>Defects</dt><dd>{pct(l['defect_rate'])}</dd></div>
            <div><dt>Downtime</dt><dd>{pct(l['downtime_pct'])}</dd></div>
            <div><dt>Short</dt><dd>{l['shortfall_units']:,.0f}</dd></div>
          </dl>
        </div>"""

    # ---- Machines -------------------------------------------------------
    machine_rows = "".join(
        f"""<li class="mrow {TIER_CLASS[m['tier']]}">
          <span class="rank">{i}</span>
          <span class="mid">{esc(m['machine'])}</span>
          <span class="mbar"><span style="width:{m['risk_score']*100:.1f}%"></span></span>
          <span class="mscore">{m['risk_score']:.2f}</span>
          <span class="tag">{m['tier']}</span>
          <span class="mread"><span>{m['temperature_c']:.0f} °C</span><span>{m['vibration_mm_s']:.1f} mm/s</span><span>{m['downtime_hours']:.1f} h down</span><span>{m['defects']:.0f} defects</span></span>
        </li>"""
        for i, m in enumerate(machines, 1)
    )

    # ---- Batches: used vs expected, with the expected mark --------------
    max_used = max(b["used_kg"] for b in batches)
    batch_rows = "".join(
        f"""<li class="brow">
          <div class="bhead"><span class="bid">{esc(b['batch'])}</span>
            <span class="bvar {'over' if b['variance_kg'] > 0 else 'under'}">{b['variance_kg']:+.0f} kg ({b['variance_pct']:+.1%})</span></div>
          <div class="btrack">
            <span class="bused" style="width:{b['used_kg']/max_used*100:.1f}%"></span>
            <span class="bexp" style="left:{b['expected_kg']/max_used*100:.1f}%" title="Expected {b['expected_kg']:.0f} kg"></span>
          </div>
          <div class="bmeta">{b['used_kg']:.0f} kg used, {b['expected_kg']:.0f} kg expected. {b['output']:.0f} units, {b['rejected']:.0f} rejected.</div>
        </li>"""
        for b in batches
    )

    warning_items = "".join(f"<li>{esc(x)}</li>" for x in r["warnings"])

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manufacturing Intelligence Dashboard: PrecisionWorks Industries</title>
<style>
  :root {{
    --bg:#edf1f6; --panel:#ffffff; --ink:#14233b; --muted:#5b6b82; --rule:#d9e1ea;
    --blue:#1f5bd8; --blue-soft:#e7eefc; --safety:#f6c343;
    --bad:#d1352b; --bad-soft:#fdecea; --warn:#c96a04; --warn-soft:#fdf1e1; --ok:#138a57; --ok-soft:#e3f4ec;
    --radius-lg:18px; --radius:12px;
  }}
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  @media (prefers-reduced-motion: reduce) {{ html {{ scroll-behavior:auto; }} .output-bar .seg {{ animation:none !important; }} }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
          font-family:"Avenir Next","Avenir","Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;
          font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased; }}
  b, .fig-value, .mscore, .lane-stats dd, .bvar {{ font-variant-numeric:tabular-nums; }}
  a:focus-visible, button:focus-visible {{ outline:3px solid var(--blue); outline-offset:2px; border-radius:6px; }}

  /* Top bar */
  .top {{ position:sticky; top:0; z-index:5; background:rgba(255,255,255,.92); backdrop-filter:blur(8px);
          border-bottom:1px solid var(--rule); }}
  .top-in {{ max-width:1240px; margin:0 auto; padding:.7rem 1.5rem; display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap; }}
  .mark {{ display:flex; align-items:center; gap:.6rem; font-weight:700; }}
  .mark svg {{ width:30px; height:30px; }}
  .mark small {{ display:block; font-weight:500; color:var(--muted); font-size:.78rem; line-height:1.2; }}
  .tabs {{ display:flex; gap:.2rem; margin-left:auto; flex-wrap:wrap; }}
  .tabs a {{ color:var(--muted); text-decoration:none; font-size:.88rem; padding:.4rem .75rem; border-radius:999px; }}
  .tabs a:hover {{ background:var(--blue-soft); color:var(--blue); }}

  main {{ max-width:1240px; margin:0 auto; padding:1.75rem 1.5rem 3rem; }}
  section {{ scroll-margin-top:5rem; }}

  /* Hero */
  .hero {{ background:var(--panel); border-radius:var(--radius-lg); padding:2rem 2.2rem 1.6rem; position:relative; overflow:hidden;
           box-shadow:0 1px 0 var(--rule), 0 18px 40px -28px rgba(20,35,59,.35); }}
  .hero::before {{ content:""; position:absolute; left:0; right:0; top:0; height:6px;
                   background:repeating-linear-gradient(-45deg, var(--safety) 0 14px, var(--ink) 14px 28px); }}
  .hero-top {{ display:flex; justify-content:space-between; gap:1.5rem; flex-wrap:wrap; align-items:flex-end; }}
  .kicker {{ color:var(--muted); margin:0 0 .3rem; font-size:.95rem; }}
  .hero h1 {{ margin:0; font-size:clamp(1.7rem, 3.2vw, 2.6rem); line-height:1.12; letter-spacing:-.02em; font-weight:700; max-width:22ch; }}
  .hero-note {{ max-width:34ch; color:var(--muted); font-size:.88rem; margin:0; padding:.7rem .9rem; border-radius:var(--radius);
                background:#fff8e1; border:1px solid #f1dc9a; color:#6b4e00; }}
  .output-bar {{ display:flex; height:64px; margin-top:1.8rem; border-radius:10px; overflow:hidden; background:var(--bg); }}
  .output-bar .seg {{ position:relative; min-width:0; animation:grow .9s cubic-bezier(.2,.7,.2,1) both; transform-origin:left; }}
  .output-bar .seg + .seg {{ border-left:2px solid #fff; }}
  .output-bar .seg:nth-child(2) {{ animation-delay:.08s; }} .output-bar .seg:nth-child(3) {{ animation-delay:.16s; }}
  .output-bar .seg:nth-child(4) {{ animation-delay:.3s; }} .output-bar .seg:nth-child(5) {{ animation-delay:.38s; }}
  @keyframes grow {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}
  .seg.made span {{ position:absolute; left:.8rem; top:50%; transform:translateY(-50%); color:#fff; font-size:.82rem; line-height:1.2; white-space:nowrap; }}
  .seg.made b {{ display:block; font-size:1.15rem; }}
  .lost-down {{ background:repeating-linear-gradient(-45deg, var(--warn) 0 6px, #f0a64a 6px 12px); }}
  .lost-other {{ background:repeating-linear-gradient(-45deg, #b9c4d2 0 6px, #dbe2eb 6px 12px); }}
  .bar-scale {{ display:flex; justify-content:space-between; font-size:.78rem; color:var(--muted); margin-top:.35rem; }}
  .legend {{ list-style:none; padding:0; margin:.9rem 0 0; display:flex; gap:1.4rem; flex-wrap:wrap; font-size:.88rem; }}
  .legend li {{ display:flex; align-items:center; gap:.45rem; }}
  .sw {{ width:14px; height:14px; border-radius:4px; display:inline-block; }}
  .sw.made {{ background:var(--blue); }}

  /* Figures strip */
  .figs {{ display:grid; grid-template-columns:repeat(5, 1fr); background:var(--panel); border-radius:var(--radius-lg);
           margin-top:1.1rem; border:1px solid var(--rule); }}
  .fig {{ padding:1rem 1.2rem; border-left:1px solid var(--rule); position:relative; }}
  .fig:first-child {{ border-left:0; }}
  .fig::after {{ content:""; position:absolute; left:1.2rem; bottom:0; width:28px; height:3px; border-radius:3px 3px 0 0; }}
  .fig.bad::after {{ background:var(--bad); }} .fig.warn::after {{ background:var(--warn); }} .fig.ok::after {{ background:var(--ok); }}
  .fig-label {{ color:var(--muted); font-size:.84rem; }}
  .fig-value {{ font-size:1.65rem; font-weight:700; letter-spacing:-.02em; line-height:1.25; }}
  .fig-note {{ color:var(--muted); font-size:.8rem; }}

  /* Sections */
  .row {{ display:grid; gap:1.1rem; margin-top:1.6rem; }}
  .row.two {{ grid-template-columns:1.25fr 1fr; }}
  .row.even {{ grid-template-columns:1fr 1fr; }}
  .block {{ background:var(--panel); border-radius:var(--radius-lg); border:1px solid var(--rule); padding:1.4rem 1.5rem; }}
  .block h2 {{ font-size:1.15rem; margin:0; letter-spacing:-.01em; }}
  .lede {{ color:var(--muted); font-size:.88rem; margin:.2rem 0 1.1rem; max-width:70ch; }}

  /* Attention */
  .alerts {{ display:grid; gap:.7rem; }}
  .alert {{ border-radius:var(--radius); padding:.9rem 1rem .95rem 1.1rem; border-left:5px solid; }}
  .alert.high {{ background:var(--bad-soft); border-color:var(--bad); }}
  .alert.medium {{ background:var(--warn-soft); border-color:var(--warn); }}
  .alert-head {{ display:flex; justify-content:space-between; font-size:.78rem; font-weight:600; }}
  .alert.high .sev {{ color:var(--bad); }} .alert.medium .sev {{ color:var(--warn); }}
  .state {{ color:var(--muted); background:#fff; padding:.05rem .55rem; border-radius:999px; }}
  .alert h3 {{ margin:.25rem 0 .1rem; font-size:1rem; }}
  .alert p {{ margin:0; font-size:.88rem; color:#3b4a60; }}
  .alert .suggest {{ margin-top:.45rem; color:var(--ink); }}
  .suggest span {{ font-weight:600; margin-right:.4rem; }}

  /* Next steps: ranked, so numbered */
  .steps {{ list-style:none; margin:0; padding:0; counter-reset:s; }}
  .steps li {{ counter-increment:s; position:relative; padding:.75rem 0 .75rem 2.6rem; border-top:1px solid var(--rule); font-size:.92rem; }}
  .steps li:first-child {{ border-top:0; padding-top:.2rem; }}
  .steps li::before {{ content:counter(s); position:absolute; left:0; top:.7rem; width:1.75rem; height:1.75rem; border-radius:50%;
                       background:var(--blue-soft); color:var(--blue); font-weight:700; font-size:.85rem; display:grid; place-items:center; }}
  .steps li:first-child::before {{ top:.15rem; }}

  /* Lanes */
  .lane {{ display:grid; grid-template-columns:120px 1fr auto; gap:1.2rem; align-items:center; padding:1rem 0; border-top:1px solid var(--rule); }}
  .lane:first-of-type {{ border-top:0; padding-top:.2rem; }}
  .lane-name {{ font-weight:700; display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; }}
  .lane-name small {{ width:100%; font-weight:500; color:var(--muted); font-size:.78rem; padding-left:1.1rem; }}
  .led {{ width:10px; height:10px; border-radius:50%; box-shadow:0 0 0 4px; }}
  .led.ok {{ background:var(--ok); color:var(--ok-soft); }} .led.warn {{ background:var(--warn); color:var(--warn-soft); }} .led.bad {{ background:var(--bad); color:var(--bad-soft); }}
  .lane-track {{ display:flex; height:34px; border-radius:8px; overflow:hidden; background:var(--bg); }}
  .lt + .lt {{ border-left:2px solid #fff; }}
  .lt.made {{ background:var(--blue); position:relative; }}
  .lt.made span {{ position:absolute; left:.7rem; top:50%; transform:translateY(-50%); color:#fff; font-weight:700; font-size:.9rem; }}
  .lane-stats {{ display:grid; grid-template-columns:repeat(4, 76px); margin:0; }}
  .lane-stats div {{ text-align:right; }}
  .lane-stats dt {{ color:var(--muted); font-size:.75rem; }}
  .lane-stats dd {{ margin:0; font-weight:700; }}

  /* Machines */
  .mlist, .blist {{ list-style:none; margin:0; padding:0; }}
  .mrow {{ display:grid; grid-template-columns:1.6rem 52px 1fr 40px 64px; gap:.7rem; align-items:center; padding:.7rem 0; border-top:1px solid var(--rule); }}
  .mrow:first-child {{ border-top:0; padding-top:.1rem; }}
  .rank {{ color:var(--muted); font-size:.82rem; }}
  .mid {{ font-weight:700; }}
  .mbar {{ height:10px; background:var(--bg); border-radius:999px; overflow:hidden; }}
  .mbar span {{ display:block; height:100%; border-radius:999px; }}
  .mrow.high .mbar span {{ background:var(--bad); }} .mrow.medium .mbar span {{ background:var(--warn); }} .mrow.low .mbar span {{ background:var(--ok); }}
  .mscore {{ text-align:right; font-weight:600; font-size:.9rem; }}
  .tag {{ font-size:.76rem; font-weight:700; padding:.12rem .6rem; border-radius:999px; text-align:center; }}
  .mrow.high .tag {{ background:var(--bad-soft); color:var(--bad); }}
  .mrow.medium .tag {{ background:var(--warn-soft); color:var(--warn); }}
  .mrow.low .tag {{ background:var(--ok-soft); color:var(--ok); }}
  .mread {{ grid-column:3 / 6; display:flex; gap:.4rem; flex-wrap:wrap; margin-top:-.2rem; }}
  .mread span {{ font-size:.76rem; color:var(--muted); background:var(--bg); padding:.05rem .5rem; border-radius:6px; }}

  /* Batches */
  .brow {{ padding:.75rem 0; border-top:1px solid var(--rule); }}
  .brow:first-child {{ border-top:0; padding-top:.1rem; }}
  .bhead {{ display:flex; justify-content:space-between; }}
  .bid {{ font-weight:700; }}
  .bvar {{ font-weight:700; font-size:.9rem; }}
  .bvar.over {{ color:var(--warn); }} .bvar.under {{ color:var(--ok); }}
  .btrack {{ position:relative; height:12px; background:var(--bg); border-radius:999px; margin:.45rem 0 .35rem; }}
  .bused {{ position:absolute; left:0; top:0; bottom:0; border-radius:999px; background:linear-gradient(90deg, #8fb0f2, var(--blue)); }}
  .bexp {{ position:absolute; top:-5px; bottom:-5px; width:3px; margin-left:-1.5px; background:var(--ink); border-radius:2px; }}
  .bmeta {{ color:var(--muted); font-size:.8rem; }}
  .key {{ display:flex; gap:1rem; font-size:.8rem; color:var(--muted); margin:-.5rem 0 1rem; }}
  .key i {{ display:inline-block; vertical-align:middle; margin-right:.35rem; }}

  /* Checks */
  .checks {{ list-style:none; margin:0; padding:0; display:grid; grid-template-columns:1fr 1fr; gap:.6rem; }}
  .checks li {{ background:#fff8e1; border:1px solid #f1dc9a; border-radius:var(--radius); padding:.7rem .9rem .7rem 2.3rem; font-size:.88rem; position:relative; }}
  .checks li::before {{ content:"!"; position:absolute; left:.8rem; top:.72rem; width:1.05rem; height:1.05rem; border-radius:50%;
                        background:var(--safety); color:var(--ink); font-weight:800; font-size:.72rem; display:grid; place-items:center; }}

  /* How it works: a real sequence */
  .flow {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:0; counter-reset:f; }}
  .flow div {{ counter-increment:f; padding:0 1rem 0 0; position:relative; }}
  .flow div::before {{ content:counter(f); display:grid; place-items:center; width:2rem; height:2rem; border-radius:50%;
                       background:var(--ink); color:#fff; font-weight:700; margin-bottom:.6rem; position:relative; z-index:1; }}
  .flow div::after {{ content:""; position:absolute; top:1rem; left:2rem; right:0; height:2px; background:var(--rule); }}
  .flow div:last-child::after {{ display:none; }}
  .flow h3 {{ margin:0; font-size:.98rem; }}
  .flow p {{ margin:.2rem 0 0; color:var(--muted); font-size:.86rem; }}

  footer {{ color:var(--muted); font-size:.8rem; margin-top:2rem; text-align:center; }}

  @media (max-width:1000px) {{
    .figs {{ grid-template-columns:repeat(2, 1fr); }}
    .fig {{ border-left:0; border-top:1px solid var(--rule); }}
    .row.two, .row.even, .checks {{ grid-template-columns:1fr; }}
    .lane {{ grid-template-columns:1fr; gap:.6rem; }}
    .lane-stats {{ grid-template-columns:repeat(4, 1fr); }}
    .lane-stats div {{ text-align:left; }}
    .flow {{ grid-template-columns:1fr 1fr; row-gap:1.2rem; }}
    .flow div::after {{ display:none; }}
    .tabs {{ margin-left:0; }}
  }}
  @media (max-width:560px) {{ .top {{ position:static; }} .hero {{ padding:1.6rem 1.2rem 1.2rem; }} .seg.made span {{ display:none; }} .figs {{ grid-template-columns:1fr; }} }}
</style></head>
<body>
<header class="top"><div class="top-in">
  <div class="mark">
    <svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#14233b"/>
      <rect x="7" y="17" width="4" height="8" rx="1" fill="#6c98ef"/><rect x="14" y="12" width="4" height="13" rx="1" fill="#3f78e6"/>
      <rect x="21" y="7" width="4" height="18" rx="1" fill="#f6c343"/></svg>
    <div>Manufacturing Intelligence<small>PrecisionWorks Industries, Track B prototype</small></div>
  </div>
  <nav class="tabs" aria-label="Sections">
    <a href="#attention">Attention</a><a href="#lines">Lines</a><a href="#machines">Machines</a>
    <a href="#materials">Material</a><a href="#checks">Data checks</a><a href="#how">How it works</a>
  </nav>
</div></header>

<main>
  <section class="hero" id="snapshot">
    <div class="hero-top">
      <div>
        <p class="kicker">One-day snapshot: three lines, six machines</p>
        <h1>{actual:,.0f} of {target:,.0f} units made. {esc(worst_line['line'])} is losing the most output.</h1>
      </div>
      <p class="hero-note"><strong>Illustrative data.</strong> Figures come from the case study tables, not a real factory. Nothing here changes records, and a person approves every action.</p>
    </div>
    {hero_bar}
  </section>

  <div class="figs">{figures_html}</div>

  <div class="row two">
    <section class="block" id="attention">
      <h2>Needs attention</h2>
      <p class="lede">Ranked by impact. Each item waits for a person to review it.</p>
      <div class="alerts">{attention_html}</div>
    </section>
    <section class="block" id="actions">
      <h2>Suggested next steps</h2>
      <p class="lede">For a manager or engineer to decide on. Generated from the rules in analysis.py.</p>
      <ol class="steps">{action_html}</ol>
    </section>
  </div>

  <div class="row">
    <section class="block" id="lines">
      <h2>Production lines</h2>
      <p class="lede">Each bar is the line's daily target. Blue is what was made; amber stripes are output lost to downtime; grey stripes are lost output with no recorded cause. OEE is an estimate: achievement × quality.</p>
      {lane_html}
    </section>
  </div>

  <div class="row even">
    <section class="block" id="machines">
      <h2>Machine risk</h2>
      <p class="lede">Weighted rule: vibration 35%, temperature 25%, downtime 20%, defects 20%, scaled to the highest value in the sample. High is 0.75 or more. Check against manufacturer alarm limits.</p>
      <ol class="mlist">{machine_rows}</ol>
    </section>
    <section class="block" id="materials">
      <h2>Material by batch</h2>
      <p class="lede">Material used against what the batch should have needed.</p>
      <div class="key"><span><i class="sw" style="background:var(--blue)"></i>Used</span><span><i class="sw" style="width:3px;background:var(--ink)"></i>Expected</span></div>
      <ul class="blist">{batch_rows}</ul>
    </section>
  </div>

  <div class="row">
    <section class="block" id="checks">
      <h2>Data checks</h2>
      <p class="lede">Gaps and inconsistencies in the input data. Resolve these before trusting any single number.</p>
      <ul class="checks">{warning_items}</ul>
    </section>
  </div>

  <div class="row">
    <section class="block" id="how">
      <h2>How it works</h2>
      <p class="lede">The same loop every week, so anyone on the team can follow and check it.</p>
      <div class="flow">
        <div><h3>Detect</h3><p>Rules and KPIs flag lines, machines and batches that need a look.</p></div>
        <div><h3>Explain</h3><p>Every number shows its inputs and formula, so it can be challenged.</p></div>
        <div><h3>Approve</h3><p>A person reviews each item and decides what to do. Nothing is automatic.</p></div>
        <div><h3>Learn</h3><p>Recorded outcomes become the labels a future model would need.</p></div>
      </div>
    </section>
  </div>

  <footer>Generated by build_dashboard.py from analysis.py. Edit the CSV files in data/ and re-run to refresh.</footer>
</main>
</body></html>
"""
    OUT.write_text(page, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    print("Wrote", build())
