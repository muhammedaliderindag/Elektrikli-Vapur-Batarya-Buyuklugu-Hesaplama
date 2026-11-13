# vapur-opt

Elektrikli vapur ağlarında batarya kapasitesi ve şarj iskelesi yerleşiminin eş zamanlı optimizasyonu
(TÜBİTAK 2209-A araştırma önerisi, İstanbul örneği). Sürüm 0.1.0: yazılım temeli.

## İçerik

| Modül | Öneri bölümü | Açıklama |
| --- | --- | --- |
| `vapur_opt/energy.py` | 2.3, Ek 5 | Güç–hız ilişkisi, sefer enerjisi, dizel ve şebeke CO₂ hesabı |
| `vapur_opt/instance.py` | Ek 2 | Problem örneği veri yapısı ve sentetik test ağı |
| `vapur_opt/milp.py` | 2.4, Ek 2 | (1)–(7) kısıtlı MILP modeli, PuLP + HiGHS |
| `vapur_opt/simulate.py` | Ek 2 | Açgözlü şarj simülasyonu ("maks" ve "ihtiyac" kuralları) |
| `vapur_opt/ga.py` | 2.4, Ek 2 | Genetik algoritma |
| `vapur_opt/check.py` | Ek 4 | Bağımsız çözüm doğrulama betiği |
| `vapur_opt/metrics.py` | Ek 5 | Re, Ri, optimallik farkı |
| `vapur_opt/schemas.py` | Ek 4 | CSV şemaları ve kalite kontrol kuralları |

## Çalıştırma

```bash
pip install "pulp==2.9.0" highspy pandas matplotlib pytest
python -m pytest -q tests
python scripts/demo_sentetik.py --runs 30
```

> Sentetik test ağındaki enerji ve maliyet değerleri yer tutucudur; gerçek veri değildir.
