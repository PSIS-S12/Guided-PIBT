# Guided-PIBT Eksperimenti

## 1. Izvedeni eksperimenti

### Prvi experiment (SP-R100 - Baseline)
Osnovni voden pristop brez dodatne optimizacije.
- **Kompilacija:**
  cmake -B build-gp ./guided-pibt -DGUIDANCE=ON -DGUIDANCE_LNS=OFF -DFLOW_GUIDANCE=OFF -DINIT_PP=ON -DRELAX=100 -DOBJECTIVE=1 -DFOCAL_SEARCH=OFF -DCMAKE_BUILD_TYPE=RELEASE
  make -C build-gp
- **Zagon:**
  ./build-gp/lifelong --inputFile guided-pibt/benchmark-lifelong/sortation_small_0_800.json --planTimeLimit 10 --output results/SP-R100/output_gp_100.json -l results/SP-R100/log_gp_100.txt

Rezultati: [SP-R100](results/SP-R100)

### Drugi experiment (GP-R100-F2 - Optimizacija)
Voden pristop z uporabo Focal Search (faktor 2) za hitrejše reševanje konfliktov.
- **Kompilacija:**
  cmake -B build-focal ./guided-pibt -DGUIDANCE=ON -DGUIDANCE_LNS=OFF -DFLOW_GUIDANCE=OFF -DINIT_PP=ON -DRELAX=100 -DOBJECTIVE=1 -DFOCAL_SEARCH=2 -DCMAKE_BUILD_TYPE=RELEASE
  make -C build-focal
- **Zagon:**
  ./build-focal/lifelong --inputFile guided-pibt/benchmark-lifelong/sortation_small_0_800.json --planTimeLimit 10 --output results/GP-R100-F2/output_focal_100.json -l results/GP-R100-F2/log_focal_100.txt

Rezultati: [GP-R100-F2](results/GP-R100-F2)

---

## 2. Opis datotek in ključnih vrednosti

### JSON datoteka (npr. output_gp_100.json)
Povzetek rezultatov za statistično analizo in poročilo.
- **Throughput:** Število opravljenih nalog na časovno enoto (glavna metrika uspeha).
- **Service Time:** Povprečen čas agenta od prejema do izpolnitve naloge.
- **Finished Tasks:** Skupno število nalog, opravljenih v 10 sekundah.
- **Num of Agents:** Število simuliranih agentov (v našem primeru 100).

### TXT datoteka (npr. log_gp_100.txt)
Podroben dnevnik dogodkov (Event Log) za vsak časovni korak.
- **Task Assignment:** Kdaj je agent prejel nalogo.
- **Movement:** Premiki agentov med koordinatami.
- **Task Completion:** Točen čas dosega cilja.
- **Wait/Conflict:** Beleženje zastojev, ko agenti čakajo zaradi blokiranih poti.