"""Sarj iskelesi secimi ve batarya kapasitesi icin MILP modeli (oneri Ek 2).

Kisitlar (1)-(7) oneri Ek 2'deki numaralarla ayni sirada kodlanmistir.
Cozucu: PuLP uzerinden acik kaynak HiGHS.
"""
from __future__ import annotations

import time

import pulp

from .instance import Instance


def solve_milp(inst: Instance, discrete_battery: bool = True, time_limit_s: int = 300, msg: bool = False) -> dict:
    m = pulp.LpProblem("sarj_batarya", pulp.LpMinimize)
    I, J, K = inst.piers, range(len(inst.charger_kw)), inst.classes
    L = range(len(inst.battery_levels_kwh))
    bmax = max(inst.battery_levels_kwh)

    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary") for i in I for j in J}
    if discrete_battery:
        y = {(k, l): pulp.LpVariable(f"y_{k}_{l}", cat="Binary") for k in K for l in L}
        B = {k: pulp.lpSum(inst.battery_levels_kwh[l] * y[k, l] for l in L) for k in K}
        for k in K:
            m += pulp.lpSum(y[k, l] for l in L) == 1, f"tek_duzey_{k}"
    else:
        Bv = {k: pulp.LpVariable(f"B_{k}", lowBound=0, upBound=bmax) for k in K}
        B = {k: Bv[k] for k in K}

    E, q, u = {}, {}, {}
    for v in inst.vessels:
        S = len(v.trips)
        for s in range(S + 1):
            E[v.vessel_id, s] = pulp.LpVariable(f"E_{v.vessel_id}_{s}", lowBound=0)
        for s in range(S):
            q[v.vessel_id, s] = pulp.LpVariable(f"q_{v.vessel_id}_{s}", lowBound=0)
            u[v.vessel_id, s] = pulp.LpVariable(f"u_{v.vessel_id}_{s}", lowBound=0)

    # Amac fonksiyonu
    m += (
        pulp.lpSum(inst.charger_cost[j] * x[i, j] for i in I for j in J)
        + pulp.lpSum(inst.battery_cost_per_kwh * inst.n_k(k) * B[k] for k in K)
        + inst.days * pulp.lpSum(
            inst.elec_price * q[key] / inst.eta_c + inst.unmet_cost * u[key] for key in q
        )
    )

    for v in inst.vessels:
        vid, Bk = v.vessel_id, B[v.vessel_class]
        for s, t in enumerate(v.trips):
            after = E[vid, s] - t.energy_kwh + u[vid, s]
            m += E[vid, s + 1] == after + q[vid, s], f"c1_{vid}_{s}"                     # (1)
            m += after >= inst.soc_min * Bk, f"c2_{vid}_{s}"                             # (2)
            m += after + q[vid, s] <= inst.soc_max * Bk, f"c3_{vid}_{s}"                 # (3)
            power = pulp.lpSum(inst.charger_kw[j] * x[t.wait_pier, j] for j in J) if t.wait_pier in I else 0
            m += q[vid, s] <= inst.eta_c * t.wait_h * power, f"c4_{vid}_{s}"           # (4)
            m += q[vid, s] <= inst.c_max * t.wait_h * Bk, f"c5_{vid}_{s}"              # (5)
        m += E[vid, 0] == inst.soc_max * Bk, f"c7_{vid}"                                 # (7)
    for i in I:
        m += pulp.lpSum(x[i, j] for j in J) <= 1, f"c6_{i}"                              # (6)

    solver = pulp.HiGHS(msg=msg, timeLimit=time_limit_s)
    t0 = time.perf_counter()
    m.solve(solver)
    runtime = time.perf_counter() - t0

    chargers = {i: j for i in I for j in J if (x[i, j].value() or 0) > 0.5}
    battery = {k: float(pulp.value(B[k])) for k in K}
    traj = {}
    for v in inst.vessels:
        vid, S = v.vessel_id, len(v.trips)
        traj[vid] = {
            "E": [E[vid, s].value() for s in range(S + 1)],
            "q": [q[vid, s].value() for s in range(S)],
            "u": [u[vid, s].value() for s in range(S)],
        }
    return {
        "method": "MILP",
        "status": pulp.LpStatus[m.status],
        "objective": pulp.value(m.objective),
        "chargers": chargers,
        "battery_kwh": battery,
        "trajectories": traj,
        "runtime_s": runtime,
        "n_vars": len(m.variables()),
        "n_cons": len(m.constraints),
    }
