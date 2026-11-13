"""Genetik algoritma (oneri Ek 2, baslangic tasarimi).

Kromozom: |I| uzunlugunda iskele genleri (0: unite yok, 1..|J|: guc duzeyi)
+ |K| uzunlugunda batarya duzeyi genleri (0..|L|-1).
Operatorler: turnuva secimi, tek noktali caprazlama, duzey degistiren mutasyon, elitizm.
"""
from __future__ import annotations

import random
import time

from .instance import Instance
from .simulate import simulate


def decode(inst: Instance, chrom: list[int]) -> tuple[dict, dict]:
    nI = len(inst.piers)
    chargers = {inst.piers[i]: g - 1 for i, g in enumerate(chrom[:nI]) if g > 0}
    battery = {k: float(inst.battery_levels_kwh[g]) for k, g in zip(inst.classes, chrom[nI:])}
    return chargers, battery


def run_ga(
    inst: Instance,
    seed: int,
    pop_size: int = 100,
    generations: int = 300,
    cx_rate: float = 0.8,
    tournament: int = 3,
    elite: int = 2,
    initial: list[list[int]] | None = None,
    rule: str = "maks",
) -> dict:
    rng = random.Random(seed)
    nI, nK = len(inst.piers), len(inst.classes)
    gene_max = [len(inst.charger_kw)] * nI + [len(inst.battery_levels_kwh) - 1] * nK
    L = nI + nK
    mut_rate = 1.0 / L
    cache: dict[tuple, float] = {}

    def fitness(c: list[int]) -> float:
        key = tuple(c)
        if key not in cache:
            ch, b = decode(inst, c)
            cache[key] = simulate(inst, ch, b, rule)["objective"]
        return cache[key]

    pop = [list(c) for c in (initial or [])][:pop_size]
    while len(pop) < pop_size:
        pop.append([rng.randint(0, gene_max[g]) for g in range(L)])

    t0 = time.perf_counter()
    history = []
    for _ in range(generations):
        scored = sorted(pop, key=fitness)
        history.append(fitness(scored[0]))
        new = [list(c) for c in scored[:elite]]
        while len(new) < pop_size:
            p1 = min(rng.sample(pop, tournament), key=fitness)
            p2 = min(rng.sample(pop, tournament), key=fitness)
            if rng.random() < cx_rate:
                cut = rng.randint(1, L - 1)
                child = p1[:cut] + p2[cut:]
            else:
                child = list(p1)
            for g in range(L):
                if rng.random() < mut_rate:
                    child[g] = rng.randint(0, gene_max[g])
            new.append(child)
        pop = new
    best = min(pop, key=fitness)
    runtime = time.perf_counter() - t0
    ch, b = decode(inst, best)
    sol = simulate(inst, ch, b, rule)
    sol.update({"method": f"GA-{rule}", "rule": rule, "seed": seed, "runtime_s": runtime, "history": history,
                "chromosome": best, "evaluations": len(cache)})
    return sol
