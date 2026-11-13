import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vapur_opt import energy, schemas
from vapur_opt.check import verify
from vapur_opt.instance import toy_instance
from vapur_opt.milp import solve_milp
from vapur_opt.simulate import simulate


def test_ornek_hesap_ek5():
    """Oneri Ek 5: 400 kW, 20 dk -> ~133 kWh, ~28,1 kg yakit, ~90 kg CO2; sebekeden ~148 kWh, ~70 kg CO2."""
    mech = energy.propulsion_power_kw(10, 400, 10) * 20 / 60
    assert mech == pytest.approx(133.3, abs=0.1)
    assert energy.diesel_fuel_kg(mech) == pytest.approx(28.1, abs=0.1)
    assert energy.diesel_co2_kg(mech) == pytest.approx(90.1, abs=0.2)
    grid = mech / 0.90
    assert grid == pytest.approx(148.1, abs=0.1)
    assert energy.grid_co2_kg(grid) == pytest.approx(70.2, abs=0.1)


def test_kubik_guc_iliskisi():
    assert energy.propulsion_power_kw(5, 400, 10) == pytest.approx(50.0)


def test_milp_cozumu_kisitlari_saglar():
    inst = toy_instance()
    sol = solve_milp(inst)
    assert sol["status"] == "Optimal"
    assert verify(inst, sol)["ok"]


def test_kontrol_betigi_ihlali_yakalar():
    inst = toy_instance()
    sol = simulate(inst, {}, {k: 400.0 for k in inst.classes})
    sol["trajectories"][inst.vessels[0].vessel_id]["q"][0] = 50.0  # sarj unitesi olmadan sarj
    res = verify(inst, sol)
    assert not res["ok"]
    assert any(e.startswith("(") for e in res["errors"])


def test_kalite_kontrol_kurallari():
    ais = pd.DataFrame({"sog_kn": [10, 30, 12]})
    assert len(schemas.drop_outliers(ais)) == 2
    assert schemas.is_berthed(41.0, 29.0, 0.5, 41.0005, 29.0)       # ~55 m
    assert not schemas.is_berthed(41.0, 29.0, 0.5, 41.003, 29.0)    # ~330 m
    assert schemas.has_gap(pd.Series(["2026-11-01 08:00", "2026-11-01 08:07"]))
    assert schemas.tariff_coverage(96, 100) == (0.96, True)
