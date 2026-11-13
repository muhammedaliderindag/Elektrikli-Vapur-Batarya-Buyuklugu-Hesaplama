"""Verilen sarj iskelesi ve batarya secimi icin acgozlu sarj simulasyonu (oneri Ek 2, GA degerlendirmesi).

Kural: Gemi gune dolu bataryayla (SoC_max) baslar. Her seferden sonra doluluk
SoC_min altina dusecekse eksik kisim karsilanamayan enerji (u) sayilir. Sarj
unitesi olan iskelede bekleme suresinin, sarj gucunun, sarj orani sinirinin ve
SoC_max'in izin verdigi kadar sarj edilir.
"""
from __future__ import annotations

from .instance import Instance


def simulate(inst: Instance, chargers: dict[str, int], battery_kwh: dict[str, float],
             rule: str = "maks") -> dict:
    """rule="maks": izin verilen en fazla sarj (oneri Ek 2).
    rule="ihtiyac": en fazla, zincirin kalan seferleri icin gereken kadar sarj
    (gun sonunda gereksiz doldurmayi onler; elektrikli sefer orani degismez).
    """
    trajectories = {}
    elec_kwh = 0.0
    unmet_kwh = 0.0
    for v in inst.vessels:
        Bk = battery_kwh[v.vessel_class]
        E = inst.soc_max * Bk
        Es, qs, us = [E], [], []
        remaining = [sum(t.energy_kwh for t in v.trips[s + 1:]) for s in range(len(v.trips))]
        for s, t in enumerate(v.trips):
            after = E - t.energy_kwh
            u = max(0.0, inst.soc_min * Bk - after)
            after += u
            q = 0.0
            j = chargers.get(t.wait_pier)
            if j is not None and t.wait_h > 0:
                q = min(
                    inst.eta_c * t.wait_h * inst.charger_kw[j],
                    inst.c_max * t.wait_h * Bk,
                    max(0.0, inst.soc_max * Bk - after),
                )
                if rule == "ihtiyac":
                    q = min(q, max(0.0, remaining[s] + inst.soc_min * Bk - after))
            E = after + q
            Es.append(E); qs.append(q); us.append(u)
            elec_kwh += q / inst.eta_c
            unmet_kwh += u
        trajectories[v.vessel_id] = {"E": Es, "q": qs, "u": us}

    capex = sum(inst.charger_cost[j] for j in chargers.values())
    capex += sum(inst.battery_cost_per_kwh * inst.n_k(k) * battery_kwh[k] for k in inst.classes)
    opex = inst.days * (inst.elec_price * elec_kwh + inst.unmet_cost * unmet_kwh)
    return {"objective": capex + opex, "trajectories": trajectories,
            "chargers": dict(chargers), "battery_kwh": dict(battery_kwh)}
