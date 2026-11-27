"""Track B prototype: manufacturing KPIs, machine risk scoring and data checks.

Standard library only. All inputs are the illustrative tables from the
Veltris case study (Dataset B1-B4). Nothing here is a measured result.
"""

import csv
from pathlib import Path

SCHEDULED_HOURS_PER_DAY = 16  # brief: each line runs 16 scheduled hours per day

# Transparent weighted rule (not a trained model). Weights sum to 1.0.
RISK_WEIGHTS = {"vibration": 0.35, "temperature": 0.25, "downtime": 0.20, "defects": 0.20}
RISK_HIGH = 0.75
RISK_MEDIUM = 0.50

DATA_DIR = Path(__file__).parent / "data"


def load_inputs(data_dir=DATA_DIR):
    """Return the three Track B tables as lists of dicts with numeric fields."""
    def load(name, numeric):
        rows = []
        with open(Path(data_dir) / name, newline="") as f:
            for row in csv.DictReader(f):
                for key in numeric:
                    row[key] = float(row[key])
                rows.append(row)
        return rows

    lines = load("line_production.csv", ["daily_target", "actual_output",
                                         "defective_units", "downtime_hours_per_day"])
    machines = load("machine_readings.csv", ["temperature_c", "vibration_mm_s",
                                             "downtime_hours", "defects"])
    batches = load("batch_material.csv", ["material_used_kg", "expected_material_kg",
                                          "actual_output", "rejected_units"])
    return lines, machines, batches


def line_kpis(lines, hours=SCHEDULED_HOURS_PER_DAY):
    """Per-line KPIs. OEE is an estimate: achievement x quality (see README)."""
    results = []
    for row in lines:
        target = row["daily_target"]
        actual = row["actual_output"]
        defects = row["defective_units"]
        downtime = row["downtime_hours_per_day"]
        achievement = actual / target
        quality = (actual - defects) / actual
        results.append({
            "line": row["production_line"],
            "achievement": achievement,
            "defect_rate": defects / actual,
            "downtime_pct": downtime / hours,
            "availability": 1 - downtime / hours,
            "quality": quality,
            "oee_estimate": achievement * quality,
            "shortfall_units": target - actual,
            # Units lost to downtime if each downtime hour had run at the target rate.
            "downtime_loss_units": downtime * target / hours,
        })
    for r in results:
        r["unexplained_shortfall_units"] = r["shortfall_units"] - r["downtime_loss_units"]
    return results


def machine_risk(machines):
    """Score each machine 0-1 against the highest value seen in the sample."""
    maxima = {
        "vibration": max(m["vibration_mm_s"] for m in machines),
        "temperature": max(m["temperature_c"] for m in machines),
        "downtime": max(m["downtime_hours"] for m in machines),
        "defects": max(m["defects"] for m in machines),
    }
    scored = []
    for m in machines:
        parts = {
            "vibration": m["vibration_mm_s"] / maxima["vibration"],
            "temperature": m["temperature_c"] / maxima["temperature"],
            "downtime": m["downtime_hours"] / maxima["downtime"],
            "defects": m["defects"] / maxima["defects"],
        }
        score = sum(RISK_WEIGHTS[k] * v for k, v in parts.items())
        if score >= RISK_HIGH:
            tier = "High"
        elif score >= RISK_MEDIUM:
            tier = "Medium"
        else:
            tier = "Low"
        scored.append({"machine": m["machine_id"], "risk_score": score, "tier": tier,
                       "temperature_c": m["temperature_c"],
                       "vibration_mm_s": m["vibration_mm_s"],
                       "downtime_hours": m["downtime_hours"], "defects": m["defects"]})
    scored.sort(key=lambda r: r["risk_score"], reverse=True)
    return scored


def batch_material(batches):
    results = []
    for b in batches:
        used, expected = b["material_used_kg"], b["expected_material_kg"]
        results.append({
            "batch": b["batch_id"],
            "used_kg": used,
            "expected_kg": expected,
            "variance_kg": used - expected,
            "variance_pct": (used - expected) / expected,
            "output": b["actual_output"],
            "rejected": b["rejected_units"],
        })
    return results


def data_checks(lines, machines, batches):
    """Return human-readable warnings about inconsistencies between tables."""
    warnings = []
    line_downtime = sum(l["downtime_hours_per_day"] for l in lines)
    machine_downtime = sum(m["downtime_hours"] for m in machines)
    if abs(line_downtime - machine_downtime) > 1e-9:
        warnings.append(f"Downtime mismatch: lines total {line_downtime:.1f} h, "
                        f"machines total {machine_downtime:.1f} h. Machines have no line ID, "
                        "so they cannot be reconciled.")
    line_defects = sum(l["defective_units"] for l in lines)
    machine_defects = sum(m["defects"] for m in machines)
    if line_defects != machine_defects:
        warnings.append(f"Defect mismatch: lines total {line_defects:.0f}, "
                        f"machines total {machine_defects:.0f}.")
    line_outputs = {l["actual_output"] for l in lines}
    for b in batches:
        if b["actual_output"] not in line_outputs:
            warnings.append(f"Batch {b['batch_id']} (output {b['actual_output']:.0f}) matches "
                            "no production line. Its line of origin is unknown.")
    warnings.append("Line data covers one day, but the brief's evaluation period is 30 days. "
                    "No monthly figure can be computed from this data.")
    warnings.append("Machine readings have no timestamps and arrive at irregular intervals, "
                    "so they cannot be linked to specific downtime events.")
    return warnings


def alerts(line_results, machine_results, batch_results):
    """Plain-language alerts for maintenance and production managers."""
    out = []
    worst_line = min(line_results, key=lambda r: r["achievement"])
    out.append(f"{worst_line['line']} has the lowest achievement "
               f"({worst_line['achievement']:.1%}) and accounts for "
               f"{worst_line['shortfall_units']:.0f} of the "
               f"{sum(r['shortfall_units'] for r in line_results):.0f} missing units.")
    for m in machine_results:
        if m["tier"] == "High":
            out.append(f"{m['machine']} is High risk (score {m['risk_score']:.2f}): "
                       f"{m['temperature_c']:.0f} °C, {m['vibration_mm_s']:.1f} mm/s, "
                       f"{m['downtime_hours']:.1f} h downtime, {m['defects']:.0f} defects. "
                       "Inspect against the manufacturer's alarm limits.")
    for b in batch_results:
        if b["variance_pct"] > 0.05:
            out.append(f"{b['batch']} used {b['variance_pct']:.1%} more material than expected "
                       f"(+{b['variance_kg']:.0f} kg).")
    return out


def run_all(data_dir=DATA_DIR):
    lines, machines, batches = load_inputs(data_dir)
    line_results = line_kpis(lines)
    machine_results = machine_risk(machines)
    batch_results = batch_material(batches)
    return {
        "lines": line_results,
        "machines": machine_results,
        "batches": batch_results,
        "warnings": data_checks(lines, machines, batches),
        "alerts": alerts(line_results, machine_results, batch_results),
    }


if __name__ == "__main__":
    results = run_all()
    for r in results["lines"]:
        print(f"{r['line']}: achievement {r['achievement']:.1%}, defects {r['defect_rate']:.1%}, "
              f"downtime {r['downtime_pct']:.1%}, OEE est. {r['oee_estimate']:.1%}")
    for m in results["machines"]:
        print(f"{m['machine']}: score {m['risk_score']:.3f} ({m['tier']})")
    for w in results["warnings"]:
        print("WARNING:", w)
