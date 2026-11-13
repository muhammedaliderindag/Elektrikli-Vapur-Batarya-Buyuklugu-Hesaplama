"""Bagimsiz cozum dogrulama betigi (oneri Ek 4, 'Cozum dogrulamasi').

Bir cozumun (sarj uniteleri, batarya kapasiteleri, E/q/u yorungeleri) oneri
Ek 2'deki (1)-(7) kisitlarini sagladigini modelden bagimsiz olarak kontrol eder
ve amac fonksiyonunu yeniden hesaplar.
"""
from __future__ import annotations

from .instance import Instance

TOL = 1e-4


def verify(inst: Instance, sol: dict) -> dict:
    errors: list[str] = []
    ch, B, traj = sol["chargers"], sol["battery_kwh"], sol["trajectories"]
    # (6) her iskelede en fazla bir unite: sozluk yapisi geregi saglanir, iskele adlarini kontrol et
    for i in ch:
        if i not in inst.piers:
            errors.append(f"(6) aday olmayan iskelede unite: {i}")
    elec = unmet = 0.0
    for v in inst.vessels:
        Bk = B[v.vessel_class]
        E, q, u = traj[v.vessel_id]["E"], traj[v.vessel_id]["q"], traj[v.vessel_id]["u"]
        if abs(E[0] - inst.soc_max * Bk) > TOL * max(1, Bk):
            errors.append(f"(7) {v.vessel_id}: gun basi doluluk {E[0]:.2f} != {inst.soc_max * Bk:.2f}")
        for s, t in enumerate(v.trips):
            after = E[s] - t.energy_kwh + u[s]
            if abs(E[s + 1] - (after + q[s])) > TOL * max(1, Bk):
                errors.append(f"(1) {v.vessel_id}/{s}: enerji dengesi")
            if after < inst.soc_min * Bk - TOL * max(1, Bk):
                errors.append(f"(2) {v.vessel_id}/{s}: alt sinir ihlali ({after:.2f})")
            if after + q[s] > inst.soc_max * Bk + TOL * max(1, Bk):
                errors.append(f"(3) {v.vessel_id}/{s}: ust sinir ihlali")
            j = ch.get(t.wait_pier)
            pmax = inst.eta_c * t.wait_h * inst.charger_kw[j] if j is not None else 0.0
            if q[s] > pmax + TOL * max(1, pmax):
                errors.append(f"(4) {v.vessel_id}/{s}: sarj gucu/iskele ihlali (q={q[s]:.2f}, sinir={pmax:.2f})")
            if q[s] > inst.c_max * t.wait_h * Bk + TOL * max(1, Bk):
                errors.append(f"(5) {v.vessel_id}/{s}: sarj orani ihlali")
            if u[s] < -TOL or q[s] < -TOL:
                errors.append(f"{v.vessel_id}/{s}: negatif q veya u")
            elec += q[s] / inst.eta_c
            unmet += u[s]
    z = sum(inst.charger_cost[j] for j in ch.values())
    z += sum(inst.battery_cost_per_kwh * inst.n_k(k) * B[k] for k in inst.classes)
    z += inst.days * (inst.elec_price * elec + inst.unmet_cost * unmet)
    rel = abs(z - sol["objective"]) / max(1.0, abs(z))
    if rel > 1e-5:
        errors.append(f"Amac fonksiyonu tutarsiz: bildirilen {sol['objective']:.2f}, yeniden hesaplanan {z:.2f}")
    return {"ok": not errors, "errors": errors, "objective_recomputed": z}
