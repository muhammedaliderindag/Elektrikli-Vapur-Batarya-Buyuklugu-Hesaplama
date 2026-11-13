"""Enerji ve emisyon hesaplari (oneri Bolum 2.3 ve Ek 5).

Guc-hiz iliskisi: P = P_ref * (v / v_ref) ** n  (n baslangic degeri 3).
"""
from __future__ import annotations

from typing import Sequence

DIESEL_LHV_KJ_PER_KG = 42_700.0   # dizel alt isil deger [16]
DIESEL_CO2_T_PER_T = 3.206        # dizel CO2 donusum katsayisi [16]
GRID_EF_DAGITIM_2022 = 0.474      # kg CO2/kWh, dagitim hattina bagli tuketim noktasi [13]
GRID_EF_ILETIM_2022 = 0.442       # kg CO2/kWh, iletim hattina bagli tuketim noktasi [13]


def propulsion_power_kw(v_kn: float, p_ref_kw: float, v_ref_kn: float, n: float = 3.0) -> float:
    """Hizdaki sevk gucu (kW)."""
    if v_kn <= 0:
        return 0.0
    return p_ref_kw * (v_kn / v_ref_kn) ** n


def trip_energy_kwh(
    speeds_kn: Sequence[float],
    dt_s: float,
    p_ref_kw: float,
    v_ref_kn: float,
    hotel_kw: float = 0.0,
    n: float = 3.0,
    drivetrain_eff: float = 0.90,
    weather_margin: float = 0.0,
) -> float:
    """Hiz profili boyunca bataryadan cekilen enerji (kWh).

    speeds_kn: esit aralikli (dt_s saniye) hiz ornekleri.
    weather_margin: kotu hava payi (0.10 veya 0.20).
    """
    mech_kwh = sum(propulsion_power_kw(v, p_ref_kw, v_ref_kn, n) for v in speeds_kn) * dt_s / 3600.0
    hotel_kwh = hotel_kw * len(speeds_kn) * dt_s / 3600.0
    return (mech_kwh / drivetrain_eff + hotel_kwh) * (1.0 + weather_margin)


def diesel_fuel_kg(mech_kwh: float, engine_eff: float = 0.40) -> float:
    """Mekanik enerjiyi uretmek icin gereken dizel yakit (kg)."""
    return mech_kwh * 3600.0 / (engine_eff * DIESEL_LHV_KJ_PER_KG)


def diesel_co2_kg(mech_kwh: float, engine_eff: float = 0.40) -> float:
    return diesel_fuel_kg(mech_kwh, engine_eff) * DIESEL_CO2_T_PER_T


def grid_co2_kg(grid_kwh: float, ef_kg_per_kwh: float = GRID_EF_DAGITIM_2022) -> float:
    return grid_kwh * ef_kg_per_kwh
