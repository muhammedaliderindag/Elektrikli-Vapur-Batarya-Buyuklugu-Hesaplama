"""Sentetik test aginda MILP ve GA'nin calistirilmasi ve karsilastirilmasi.

Kullanim:  python scripts/demo_sentetik.py [--runs 30]
Ciktilar:  cikti/sonuc_senaryo_sentetik.csv, cikti/soc_yorungesi.png, cikti/ga_yakinsama.png
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from vapur_opt.check import verify
from vapur_opt.ga import run_ga
from vapur_opt.instance import toy_instance
from vapur_opt.metrics import charger_share, electric_share, optimality_gap
from vapur_opt.schemas import COLUMNS


def row(inst, sol, run_id, gap):
    return {
        "scenario_id": "SENTETIK-E-T0",
        "method": sol["method"],
        "run_id": run_id,
        "charging_piers": ";".join(f"{i}:{int(inst.charger_kw[j])}kW" for i, j in sorted(sol["chargers"].items())),
        "battery_kwh_by_class": json.dumps({k: round(b, 1) for k, b in sol["battery_kwh"].items()}),
        "cost_tl": round(sol["objective"], 0),
        "electric_share_pct": round(electric_share(inst, sol), 1),
        "co2_t": None,  # gercek veriyle hesaplanacak
        "gap_pct": None if gap is None else round(gap, 3),
        "runtime_s": round(sol["runtime_s"], 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=30)
    args = ap.parse_args()
    out = ROOT / "cikti"
    out.mkdir(exist_ok=True)

    inst = toy_instance()
    print(f"Ornek: {inst.name} | {len(inst.piers)} aday iskele, {len(inst.vessels)} gemi, {inst.n_trips} sefer")

    from vapur_opt.milp import solve_milp
    milp = solve_milp(inst, discrete_battery=True)
    chk = verify(inst, milp)
    print(f"\nMILP  durum={milp['status']}  Z={milp['objective']:,.0f} TL/yil  sure={milp['runtime_s']:.2f} s"
          f"  ({milp['n_vars']} degisken, {milp['n_cons']} kisit)")
    print(f"      sarj iskeleleri={milp['chargers']}  batarya={milp['battery_kwh']}")
    print(f"      Re={electric_share(inst, milp):.1f}%  Ri={charger_share(inst, milp):.1f}%  kontrol={'GECTI' if chk['ok'] else chk['errors'][:3]}")

    rows = [row(inst, milp, 0, 0.0)]
    summary = {}
    for rule in ("maks", "ihtiyac"):
        ga_sols = []
        for seed in range(1, args.runs + 1):
            sol = run_ga(inst, seed=seed, rule=rule)
            ga_sols.append(sol)
            rows.append(row(inst, sol, seed, optimality_gap(sol["objective"], milp["objective"])))
        zs = [s["objective"] for s in ga_sols]
        gaps = [optimality_gap(z, milp["objective"]) for z in zs]
        best = min(ga_sols, key=lambda s: s["objective"])
        all_ok = all(verify(inst, s)["ok"] for s in ga_sols)
        print(f"\nGA, sarj kurali='{rule}' ({args.runs} calistirma, pop=100, kusak=300)")
        print(f"      en iyi Z={min(zs):,.0f}  ortalama={statistics.mean(zs):,.0f}  std={statistics.pstdev(zs):,.0f}")
        print(f"      optimallik farki: en iyi={min(gaps):.2f}%  ortalama={statistics.mean(gaps):.2f}%  en kotu={max(gaps):.2f}%")
        print(f"      ortalama sure={statistics.mean(s['runtime_s'] for s in ga_sols):.2f} s/calistirma")
        print(f"      en iyi cozum: sarj={best['chargers']} batarya={best['battery_kwh']}  Re={electric_share(inst, best):.1f}%")
        print(f"      tum cozumler bagimsiz kontrolden gecti: {all_ok}")
        summary[rule] = ga_sols
    ga_sols = summary["ihtiyac"]

    df = pd.DataFrame(rows, columns=COLUMNS["sonuc_senaryo.csv"])
    df.to_csv(out / "sonuc_senaryo_sentetik.csv", index=False)

    # Sekil: SoC yorungesi (MILP cozumu), her siniftan bir gemi
    fig, ax = plt.subplots(figsize=(8, 3.6))
    shown = set()
    for v in inst.vessels:
        if v.vessel_class in shown:
            continue
        shown.add(v.vessel_class)
        Bk = milp["battery_kwh"][v.vessel_class]
        tr = milp["trajectories"][v.vessel_id]
        xs, ys = [0], [tr["E"][0] / Bk * 100]
        for s, t in enumerate(v.trips):
            after = tr["E"][s] - t.energy_kwh + tr["u"][s]
            xs += [s + 0.7, s + 1]
            ys += [after / Bk * 100, tr["E"][s + 1] / Bk * 100]
        ax.plot(xs, ys, marker="o", ms=3, label=f"{v.vessel_id} ({v.vessel_class}, {Bk:.0f} kWh)")
    ax.axhline(inst.soc_min * 100, color="grey", ls="--", lw=1)
    ax.axhline(inst.soc_max * 100, color="grey", ls="--", lw=1)
    ax.set_xlabel("Sefer sırası")
    ax.set_ylabel("Batarya doluluk oranı (%)")
    ax.set_title("MILP çözümünde batarya doluluk yörüngesi (sentetik test ağı)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "soc_yorungesi.png", dpi=160)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    for s in ga_sols[:10]:
        ax.plot([h / 1e6 for h in s["history"]], lw=0.8, alpha=0.7)
    ax.axhline(milp["objective"] / 1e6, color="black", ls="--", lw=1, label="MILP optimumu")
    ax.set_xlabel("Kuşak")
    ax.set_ylabel("En iyi Z (milyon TL/yıl)")
    ax.set_title("Genetik algoritmanın yakınsaması (ihtiyaç kuralı, ilk 10 çalıştırma)")
    ax.set_ylim(milp["objective"] / 1e6 * 0.98, milp["objective"] / 1e6 * 1.4)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "ga_yakinsama.png", dpi=160)
    print(f"\nCiktilar: {out}")


if __name__ == "__main__":
    main()
