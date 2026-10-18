# Training Mall

Projektet är ombyggt så att kod, konfiguration och genererad data ligger separerade.

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
  - Central startpunkt för pipelinen.

- `app/pipeline/`
  - Manifest, katalog och orchestrator.
  - Vet vilka steg som finns, i vilken ordning de kör och vilka indata/utdata de har.

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
  - Körrapporter.
  - Pipeline-rapporter ligger i `data/reports/pipeline/`.

- `docs/`
  - Arbetsdokument och anteckningar.

- `tests/`
  - Tester som kontrollerar generatorns regler.

## Kör pipelinen steg för steg

Kör kommandona i PowerShell från projektmappen:

```powershell
cd "C:\Users\shahi\Documents\Training mall"
```

1. Lista alla tillgängliga steg:

```powershell
python .\app\main.py --list
```

2. Visa detaljer om ett specifikt steg. Exemplet visar steg 7:

```powershell
python .\app\main.py --show stage7
```

3. Testkör hela pipelinen utan att skapa eller ändra mallar:

```powershell
python .\app\main.py --dry-run
```

4. Kör hela pipelinen. Den kör steg 1 till steg 10 i ordning och sparar resultat under `data/output/`:

```powershell
python .\app\main.py
```

5. Kör bara utvalda steg. Detta är användbart när du vill kontrollera en mindre del av flödet:

```powershell
python .\app\main.py --only stage1 stage2 stage3
```

6. Kör ett sammanhängande intervall av steg:

```powershell
python .\app\main.py --from stage4 --to stage8
```

7. Hoppa över ett steg om du redan har dess resultat och vill gå vidare med resten:

```powershell
python .\app\main.py --skip stage1
```

## Principen bakom upplagget

- `app/` innehåller kod
- `config/` innehåller den gemensamma källan för regler och fördelningar
- `data/` innehåller genererad output och rapporter

Det gör det enklare att:

- byta ut ett steg utan att förstöra resten
- lägga till ett nytt steg senare
- hitta vad som är logik och vad som bara är genererad data
- köra hela eller delar av pipelinen från en enda startpunkt
