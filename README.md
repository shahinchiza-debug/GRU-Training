# Training Mall

Projektet ar nu ombyggt sa att kod, config och genererad data ligger separerade.

## Struktur

```text
training-mall/
├─ app/
│  ├─ main.py
│  ├─ pipeline/
│  ├─ shared/
│  └─ stages/
├─ config/
├─ data/
│  ├─ output/
│  ├─ reports/
│  └─ tmp/
├─ docs/
├─ tests/
├─ .gitignore
└─ README.md
```

## Vad som ligger var

- `app/main.py`
  - Central startpunkt for pipelinen.

- `app/pipeline/`
  - Manifest, katalog och orchestrator.
  - Vet vilka steg som finns, i vilken ordning de kor och vilka indata/utdata de har.

- `app/stages/`
  - Själva stegkoden.
  - Ett steg per mapp, till exempel `app/stages/stage01_raw/run.py`.

- `config/`
  - Regler, distributionsfiler och pools.
  - Har ingen generatorlogik, bara data och konfiguration.

- `data/output/`
  - Genererade mallar per steg.
  - Exempel: `data/output/stage01_raw`, `data/output/stage09_pools`.

- `data/reports/`
  - Korrapporter.
  - Pipeline-rapporter ligger i `data/reports/pipeline/`.

- `docs/`
  - Arbetsdokument och anteckningar.

- `tests/`
  - Plats for framtida tester.

## Koer pipelinen

Lista steg:

```powershell
python .\app\main.py --list
```

Visa ett steg:

```powershell
python .\app\main.py --show stage7
```

Koer hela pipelinen:

```powershell
python .\app\main.py
```

Koer bara vissa steg:

```powershell
python .\app\main.py --only stage1 stage2 stage3
```

Koer ett intervall:

```powershell
python .\app\main.py --from stage4 --to stage8
```

Dry run:

```powershell
python .\app\main.py --dry-run
```

## Principen bakom upplagget

- `app/` innehaller kod
- `config/` innehaller source-of-truth for regler och fordelningar
- `data/` innehaller genererad output och rapporter

Det gor det enklare att:

- byta ut ett steg utan att forstora resten
- lagga till ett nytt steg senare
- hitta vad som ar logik och vad som bara ar genererad data
- koera hela eller delar av pipelinen fran en enda startpunkt
