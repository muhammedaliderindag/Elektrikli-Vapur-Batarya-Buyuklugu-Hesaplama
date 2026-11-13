"""Veri yapisi ve kalite kontrol kurallari (oneri Ek 4)."""
from __future__ import annotations

import math

import pandas as pd

COLUMNS = {
    "seferler.csv": ["trip_id", "line_id", "dep_pier_id", "arr_pier_id", "dep_time", "arr_time",
                     "distance_nm", "day_type", "season"],
    "iskeleler.csv": ["pier_id", "name", "lat", "lon", "charge_candidate"],
    "ais_kayit.csv": ["mmsi", "timestamp_utc", "lat", "lon", "sog_kn", "cog_deg", "nav_status"],
    "sefer_zinciri.csv": ["vessel_id", "vessel_class", "seq", "trip_id", "wait_min", "wait_pier_id", "source"],
    "sefer_enerji.csv": ["trip_id", "vessel_class", "duration_min", "mean_speed_kn", "energy_kwh",
                         "weather_margin_pct"],
    "sonuc_senaryo.csv": ["scenario_id", "method", "run_id", "charging_piers", "battery_kwh_by_class",
                          "cost_tl", "electric_share_pct", "co2_t", "gap_pct", "runtime_s"],
}

# Baslangic esikleri (IP1 sonunda gerekirse guncellenecek)
TARIFF_COVERAGE_MIN = 0.95
PIER_MATCH_RADIUS_M = 150.0
PIER_MATCH_MAX_SOG_KN = 1.0
OUTLIER_SOG_KN = 25.0
MAX_GAP_MIN = 5.0
DURATION_DEVIATION = 0.50


def check_columns(df: pd.DataFrame, file_name: str) -> list[str]:
    """Eksik sutunlari dondurur."""
    return [c for c in COLUMNS[file_name] if c not in df.columns]


def tariff_coverage(n_structured: int, n_in_timetable: int) -> tuple[float, bool]:
    cov = n_structured / n_in_timetable
    return cov, cov >= TARIFF_COVERAGE_MIN


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def drop_outliers(ais: pd.DataFrame) -> pd.DataFrame:
    """Yer hizi 25 knot uzerindeki AIS kayitlarini eler."""
    return ais[ais["sog_kn"] <= OUTLIER_SOG_KN]


def is_berthed(lat: float, lon: float, sog_kn: float, pier_lat: float, pier_lon: float) -> bool:
    """Iskeleye 150 m'den yakin ve yer hizi 1 knot altindaysa yanasma kabul edilir."""
    return sog_kn < PIER_MATCH_MAX_SOG_KN and haversine_m(lat, lon, pier_lat, pier_lon) < PIER_MATCH_RADIUS_M


def has_gap(timestamps: pd.Series) -> bool:
    """Bir sefer icinde 5 dakikayi asan AIS boslugu var mi?"""
    ts = pd.to_datetime(timestamps).sort_values()
    return bool((ts.diff().dt.total_seconds() / 60.0 > MAX_GAP_MIN).any())


def duration_suspicious(measured_min: float, timetable_min: float) -> bool:
    return abs(measured_min - timetable_min) / timetable_min > DURATION_DEVIATION
