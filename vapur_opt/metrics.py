"""Performans gostergeleri (oneri Ek 5)."""
from __future__ import annotations

from .instance import Instance

EPS = 1e-3


def electric_share(inst: Instance, sol: dict) -> float:
    """Re: bataryadan karsilanamayan enerji olmadan (u = 0) tamamlanan seferlerin orani (%)."""
    ok = sum(1 for v in inst.vessels for u in sol["trajectories"][v.vessel_id]["u"] if u <= EPS)
    return 100.0 * ok / inst.n_trips


def charger_share(inst: Instance, sol: dict) -> float:
    """Ri: sarj unitesi kurulan iskele sayisinin aday iskele sayisina orani (%)."""
    return 100.0 * len(sol["chargers"]) / len(inst.piers)


def optimality_gap(z_ga: float, z_milp: float) -> float:
    return 100.0 * (z_ga - z_milp) / z_milp
