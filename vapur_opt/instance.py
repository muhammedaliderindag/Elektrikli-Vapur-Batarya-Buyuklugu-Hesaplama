"""Problem ornegi veri yapisi (oneri Ek 2'deki kumeler ve parametreler)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Trip:
    trip_id: str
    energy_kwh: float     # e_vs: seferin bataryadan cektigi enerji
    wait_h: float         # d_vs: seferden sonraki bekleme suresi (saat)
    wait_pier: str        # i(v,s): bekleme iskelesi


@dataclass
class Vessel:
    vessel_id: str
    vessel_class: str     # k(v)
    trips: list[Trip]     # gunluk sefer zinciri, sirali


@dataclass
class Instance:
    piers: list[str]                       # I: aday sarj iskeleleri
    charger_kw: list[float]                # P_j
    charger_cost: list[float]              # c_ij (iskeleden bagimsiz alindi), TL/yil
    classes: list[str]                     # K
    vessels: list[Vessel]                  # V
    battery_levels_kwh: list[float]        # GA ve kesikli MILP icin batarya duzeyleri
    battery_cost_per_kwh: float            # c_B, TL/kWh-yil (yilliklandirilmis)
    elec_price: float                      # p, TL/kWh
    unmet_cost: float                      # c_u, TL/kWh (tam elektrikli: ceza, hibrit: dizel)
    days: int = 365                        # D
    eta_c: float = 0.95                    # sarj verimi
    c_max: float = 1.0                     # en yuksek sarj orani (1/saat)
    soc_min: float = 0.20
    soc_max: float = 0.90
    name: str = "ornek"
    notes: dict = field(default_factory=dict)

    def n_k(self, k: str) -> int:
        return sum(1 for v in self.vessels if v.vessel_class == k)

    @property
    def n_trips(self) -> int:
        return sum(len(v.trips) for v in self.vessels)


def toy_instance(seed: int = 7) -> Instance:
    """Yazilimi sinamak icin SENTETIK kucuk ag.

    Gercek veri degildir: 8 aday iskele, 2 gemi sinifi, 6 gemi. Gemiler iki
    iskele arasinda mekik seklinde calisir; iki aktarma iskelesi (A, B) birden
    fazla hatta ortaktir. Sefer enerjileri, 400 kW ortalama guc ve 20 dakika
    sefer suresi civarinda uretilmistir (oneri Ek 5 ornek hesabi).
    """
    rng = random.Random(seed)
    piers = ["A", "B", "C", "D", "E", "F", "G", "H"]
    # (hat, iskele1, iskele2, gemi sinifi, sefer suresi dk, gemi sayisi)
    lines = [
        ("H1", "A", "C", "buyuk", 20, 1),
        ("H2", "A", "D", "buyuk", 25, 1),
        ("H3", "B", "E", "buyuk", 18, 1),
        ("H4", "B", "F", "kucuk", 12, 1),
        ("H5", "A", "G", "kucuk", 15, 1),
        ("H6", "B", "H", "kucuk", 10, 1),
    ]
    mean_kw = {"buyuk": 400.0, "kucuk": 220.0}
    vessels: list[Vessel] = []
    for line, p1, p2, cls, dur_min, nv in lines:
        for vi in range(nv):
            trips = []
            n_trips = 14
            for s in range(n_trips):
                dep, arr = (p1, p2) if s % 2 == 0 else (p2, p1)
                dur_h = dur_min * rng.uniform(0.95, 1.10) / 60.0
                e = mean_kw[cls] * dur_h / 0.90            # suruş zinciri verimi 0.90
                # aktarma iskelelerinde (A, B) bekleme daha uzun
                wait_min = rng.uniform(12, 20) if arr in ("A", "B") else rng.uniform(5, 10)
                if s == n_trips - 1:
                    wait_min = 0.0                         # gunun son seferi
                trips.append(Trip(f"{line}-{vi}-{s:02d}", round(e, 2), wait_min / 60.0, arr))
            vessels.append(Vessel(f"{line}-v{vi}", cls, trips))
    return Instance(
        piers=piers,
        charger_kw=[500.0, 1000.0],
        charger_cost=[900_000.0, 1_500_000.0],
        classes=["buyuk", "kucuk"],
        vessels=vessels,
        battery_levels_kwh=[400, 600, 800, 1000, 1200, 1500, 1800, 2200, 2600, 3000],
        battery_cost_per_kwh=2_000.0,
        elec_price=3.0,
        unmet_cost=1_000.0,
        name="sentetik_8iskele_6gemi",
        notes={"uyari": "Maliyet ve enerji degerleri yer tutucudur, gercek veri degildir."},
    )
