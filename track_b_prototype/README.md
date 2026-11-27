# Track B Prototype: Manufacturing Intelligence (PrecisionWorks Industries)

A small, transparent prototype for the Veltris case study, Challenge B. It computes factory KPIs, ranks machines by a risk rule, checks the data for inconsistencies, and writes a dashboard.

**All data is illustrative**, taken from the case study tables. The prototype does not report measured results.

## Requirements

- Python 3.9 or newer
- No third-party packages. Standard library only.

## Run it

**On a Mac:** double-click `run.command`. It runs the checks, prints the KPIs, rebuilds the dashboard and opens it in your browser. The first time, if macOS blocks it, right-click the file and choose Open.

**From a terminal:**

```bash
cd track_b_prototype
python3 -m unittest test_analysis -v   # 13 checks against hand-calculated values
python3 analysis.py                    # print KPIs and warnings to the terminal
python3 build_dashboard.py             # write dashboard.html
open dashboard.html                    # or double-click it in your file browser
```

## Files

| File | Purpose |
|---|---|
| `data/line_production.csv` | Dataset B1: target, actual output, defects and downtime per line |
| `data/machine_readings.csv` | Dataset B2: temperature, vibration, downtime and defects per machine |
| `data/batch_material.csv` | Dataset B3: material used vs expected, output and rejects per batch |
| `analysis.py` | All calculations: line KPIs, machine risk score, batch variance, data checks, alerts |
| `build_dashboard.py` | Builds the HTML dashboard from `analysis.py` |
| `test_analysis.py` | Tests that check the key numbers against hand calculations |
| `run.command` | Double-click on a Mac to run everything |
| `dashboard.html` | Generated output. Open it in any browser. |

## Method

**Line KPIs**
- Achievement = actual output ÷ daily target
- Defect rate = defective units ÷ actual output
- Downtime % = downtime hours ÷ 16 scheduled hours
- Quality = (actual − defective) ÷ actual
- OEE (estimate) = achievement × quality. This assumes the daily target is the ideal rate and ignores speed losses beyond it. It is an estimate, not a measured OEE.
- Downtime-explained shortfall = downtime hours × target ÷ 16. Whatever remains of the shortfall is left unexplained.

**Machine risk score**
- Each of four signals (vibration, temperature, downtime, defects) is divided by the highest value in the sample, then weighted: vibration 0.35, temperature 0.25, downtime 0.20, defects 0.20.
- Tiers: High ≥ 0.75, Medium ≥ 0.50, Low otherwise.
- This is a transparent rule, not a trained model. With six machines and no failure labels, a trained model would not be justified.

**Data checks**
- Machine downtime (8.9 h) does not match line downtime (5.0 h). Machine defects (84) do not match line defects (137). Machines have no line ID, so they cannot be reconciled.
- Batch B004 (820 units) matches no production line.
- The data covers one day, but the brief's evaluation period is 30 days.
- Machine readings have no timestamps.

## Limitations

- One day of data, six machines and four batches. Patterns are signals to investigate, not causes.
- Correlation between vibration, temperature and defects does not establish cause. A shared factor such as load or bearing age could explain all three.
- Risk tiers are relative to this sample, not to industry alarm limits. Check actual machines against manufacturer limits before acting on a tier.
- The 30- and 90-day impact measurements are not implemented. They require timestamped data collected over time.

## Next steps if real data becomes available

1. Add timestamps and a line ID to machine readings, so the two datasets can be reconciled.
2. Record downtime reasons and maintenance actions, so the risk score can be validated against real failures.
3. Track the KPIs weekly for 30 days before and after any intervention, so impact can be measured.
